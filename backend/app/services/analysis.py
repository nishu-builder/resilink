from pathlib import Path

import json
import math
import re
import zipfile
from datetime import datetime
from tempfile import TemporaryDirectory
from typing import Dict, Any

import geopandas as gpd
import numpy as np
import rasterio
from shapely.geometry import mapping
from app.db import get_current_session, with_async_session
from sqlmodel import select
from scipy.stats import norm
import logging
import pandas as pd

from app.models import Run, FragilityCurve, MappingSet, Hazard, BuildingDataset

# Constants
FT_TO_M = 0.3048
SQRT2 = math.sqrt(2)

logger = logging.getLogger(__name__)


def _create_mapping_dict(mapping_json: Dict[str, Any]) -> Dict[int, str]:
    """Parse mapping-set JSON -> {arch_flood_value: fragility_id}."""
    mapping: Dict[int, str] = {}
    if not mapping_json or "mappings" not in mapping_json:
        return mapping

    for rule_entry in mapping_json["mappings"]:
        # Identify fragility id (field name can vary)
        entry = rule_entry.get("entry", {})
        fragility_id = entry.get("Non-Retrofit Fragility ID Code") or entry.get(
            "FragilityID"
        ) or entry.get("fragility_id")
        if not fragility_id:
            continue

        rules = rule_entry.get("rules", {}).get("AND", [])
        arch_val = None
        for r in rules:
            if "arch_flood" in r:
                # Expected pattern: "int arch_flood EQUALS 1"
                parts = r.split()
                try:
                    if len(parts) >= 4 and parts[2].upper() == "EQUALS":
                        arch_val = int(parts[3])
                except ValueError:
                    arch_val = None
        if arch_val is not None:
            mapping[arch_val] = fragility_id
    return mapping


def calculate_fragility(fragility_curve_data: dict, wse_m: float, ffe_elev_m: float) -> dict:
    """Calculates Limit State (LS) exceedance probabilities based on fragility data.

    Args:
        fragility_curve_data (dict): JSON definition of the DFR3 set.
        wse_m (float): Water Surface Elevation in meters at the building location.
        ffe_elev_m (float): First Floor Elevation in meters of the building.

    Returns:
        dict: Dictionary mapping Limit State description (e.g., 'LS_0') to 
              exceedance probability (float).
    """
    ls_probabilities = {}
    if not fragility_curve_data or 'fragilityCurves' not in fragility_curve_data:
        print("Warning: Invalid or empty fragility curve data provided.")
        return ls_probabilities

    effective_depth_m = wse_m - ffe_elev_m

    # Regex for lognormal CDF expression: scipy.stats.norm.cdf((math.log(...) - mu) / sigma)
    pattern = re.compile(
        r'\(math\.log\([^)]+\)\s*-\s*\(?([\d\.\-+eE]+)\)?\s*\)\s*/\s*\(?([\d\.\-+eE]+)\)?')

    if effective_depth_m <= 0:
        # Water level below FFE, probability is 0 for all LS
        for curve in fragility_curve_data['fragilityCurves']:
            ls_desc = curve.get('returnType', {}).get(
                'description', f'LS_unknown_{len(ls_probabilities)}')
            ls_probabilities[ls_desc] = 0.0
        return ls_probabilities

    # Calculate probability for each defined limit state curve
    for curve in fragility_curve_data['fragilityCurves']:
        ls_desc = curve.get('returnType', {}).get(
            'description', f'LS_unknown_{len(ls_probabilities)}')
        prob = 0.0
        rule = curve.get('rules', [{}])[0]
        expression_str = rule.get('expression')

        if expression_str:
            match = pattern.search(expression_str)
            if match:
                try:
                    mu_str = match.group(1)
                    sigma_str = match.group(2)
                    mu = float(mu_str)
                    sigma = float(sigma_str)
                    log_depth = math.log(effective_depth_m)
                    if sigma == 0:
                        z_score = float('inf') if log_depth > mu else -float('inf')
                    else:
                        z_score = (log_depth - mu) / sigma
                    prob = norm.cdf(z_score)

                except (IndexError, ValueError, TypeError) as e:
                    print(f"\n--- CALCULATION ERROR after Regex Match ---")
                    print(f"Expression: '{expression_str}'")
                    print(f"Matched mu='{mu_str}', sigma='{sigma_str}'")
                    print(f"Error for {ls_desc}: {e}")
                    print(f"Effective Depth: {effective_depth_m}")
                    print(f"---------------------")
                    prob = 0.0  # Assign default on error
            else:
                # Raise error if expression doesn't match expected pattern
                raise ValueError(
                    f"Expression format not recognized for {ls_desc}: '{expression_str}'")
        else:
            print(
                f"Warning: No expression found for {ls_desc}. Setting probability to 0.")
            prob = 0.0

        ls_probabilities[ls_desc] = prob

    return ls_probabilities



@with_async_session
async def perform_analysis(run_id: int, M_OFFSET: float = 0.0) -> None:
    """Execute full damage-analysis workflow for a Run row.

    Results written to /data/results_{run_id}.geojson and Run updated.
    """
    # Get session using the accessor
    session = get_current_session()

    results_path = Path("/data") / f"results_{run_id}.geojson"

    # Fetch run using await
    run = await session.get(Run, run_id)
    if not run:
        raise ValueError(f"Run id {run_id} not found")

    # Fetch related objects using await
    hazard: Hazard | None = await session.get(Hazard, run.hazard_id)
    mapping_set: MappingSet | None = await session.get(MappingSet, run.mapping_set_id)
    building_ds: BuildingDataset | None = await session.get(BuildingDataset, run.building_dataset_id)
    if not all([hazard, mapping_set, building_ds]):
        raise ValueError("Run has invalid foreign keys")

    run.status = "RUNNING"
    session.add(run)
    await session.commit()

    try:
        # File I/O remains synchronous for now
        with open(mapping_set.json_path, "r") as f:
            mapping_json = json.load(f)
        arch_to_fragility = _create_mapping_dict(mapping_json)

        # Build fragility cache from DB curves
        fragility_cache: Dict[str, Dict[str, Any]] = {}
        # Use await for execute
        result = await session.execute(select(FragilityCurve))
        curves = result.scalars().all()
        for c in curves:
            obj = json.load(open(c.json_path, "r"))
            fragility_cache[obj["id"]] = obj

        # Ensure all fragility ids referenced in mapping exist
        missing_ids = [fid for fid in arch_to_fragility.values() if fid not in fragility_cache]
        if missing_ids:
            raise ValueError(f"Missing fragility curve(s) in DB: {missing_ids}")

        # Load WSE raster (sync)
        wse_ds = rasterio.open(hazard.wse_raster_path)

        # Extract buildings from zip (sync)
        with TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(building_ds.shp_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)

            # Find .shp file recursively (sync)
            shp_files = list(Path(tmpdir).rglob("*.shp")) # Use rglob
            if not shp_files:
                raise FileNotFoundError("No .shp file found anywhere in uploaded building dataset zip")
            # Optional: Add check if multiple .shp files are found, decide which to use
            if len(shp_files) > 1:
                # Example: raise error or log a warning and pick the first one
                # logger.warning(f"Multiple .shp files found, using {shp_files[0]}")
                pass # For now, just proceed with the first one found
            buildings_gdf = gpd.read_file(shp_files[0])

        # Iterate buildings and compute probabilities (calculations are sync)
        features = []
        for _, b in buildings_gdf.iterrows():
            try:
                guid = b.get('guid') or b.get('id') or _
                arch_val = int(b['arch_flood']) if 'arch_flood' in b and not pd.isna(b['arch_flood']) else None
                ffe_ft = float(b['ffe_elev']) if 'ffe_elev' in b and not pd.isna(b['ffe_elev']) else None
                geom = b.geometry

                if arch_val is None or ffe_ft is None or geom is None or geom.is_empty:
                    raise ValueError("Missing required attributes or geometry")

                # Sample raster (sync rasterio)
                x, y = geom.x, geom.y
                row, col = wse_ds.index(x, y)
                if not (0 <= row < wse_ds.height and 0 <= col < wse_ds.width):
                    raise ValueError("Point outside raster bounds")
                wse_arr = wse_ds.read(1, window=rasterio.windows.Window(col, row, 1, 1))
                if wse_arr.size == 0:
                    raise ValueError("Empty raster window")
                wse_val = wse_arr[0, 0]
                if not np.isfinite(wse_val):
                    raise ValueError("Raster value is nodata or non-finite")

                # Calculate ffe_m without the offset
                ffe_m = ffe_ft * FT_TO_M - M_OFFSET

                fragility_id = arch_to_fragility.get(arch_val)
                if fragility_id is None:
                    raise ValueError(f"No fragility mapping for arch_flood {arch_val}")
                curve_json = fragility_cache[fragility_id]

                ls = calculate_fragility(curve_json, wse_val, ffe_m)
                logger.info(f"ls: {ls}")
                p_ls0 = ls.get('LS_0', 0.0)
                p_ls1 = ls.get('LS_1', 0.0)
                p_ls2 = ls.get('LS_2', 0.0)

                p_ds3 = max(0.0, p_ls2)
                p_ds2 = max(0.0, p_ls1 - p_ls2)
                p_ds1 = max(0.0, p_ls0 - p_ls1)
                p_ds0 = max(0.0, 1.0 - p_ls0)

                total = p_ds0 + p_ds1 + p_ds2 + p_ds3
                if not math.isclose(total, 1.0, rel_tol=1e-6):
                    raise ValueError(f"Probabilities do not sum to 1: {total}")

                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": {
                        # "guid": guid,
                        "arch_flood": arch_val,
                        "ffe_m": ffe_m,
                        # "ffe_ft": ffe_ft,
                        # "wse_m": float(wse_val), # Ensure serializable
                        "eff_depth_m": float(wse_val - ffe_m),
                        # "fragility_id": fragility_id,
                        "P_DS0": p_ds0,
                        "P_DS1": p_ds1,
                        "P_DS2": p_ds2,
                        "P_DS3": p_ds3,
                    }
                })
            except Exception as point_error:
                guid = b.get('guid') or b.get('id') or _
                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom) if geom and not geom.is_empty else None,
                    "properties": {
                        "guid": guid,
                        "error": str(point_error)
                    }
                })

        # Create GeoJSON FeatureCollection (sync)
        results_fc = {
            "type": "FeatureCollection",
            "features": features
        }

        # Write results (sync)
        with open(results_path, "w") as f:
            json.dump(results_fc, f)
        logger.info(f"Results written to {results_path}")

        # Update Run status in DB
        run.status = "COMPLETED"
        run.result_path = str(results_path)
        run.finished_at = datetime.utcnow()
        session.add(run)
    finally:
        # Ensure raster dataset is closed (important!)
        if 'wse_ds' in locals() and wse_ds:
            wse_ds.close()
