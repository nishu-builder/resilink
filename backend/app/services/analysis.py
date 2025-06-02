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
from sqlalchemy.orm import joinedload
from scipy.stats import norm
import logging
import pandas as pd

from app.models import Run, FragilityCurve, MappingSet, Hazard, BuildingDataset, RunIntervention, Building
from app.services.financial import calculate_eal

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
    """Execute full damage-analysis workflow for a Run row with intervention support.

    Results written to /data/results_{run_id}.geojson and Run updated.
    """
    logger.info(f"Starting perform_analysis for run_id: {run_id}")
    
    # Get session using the accessor
    session = get_current_session()

    results_path = Path("/data") / f"results_{run_id}.geojson"

    try:
        # Fetch run using await
        logger.info(f"Fetching run {run_id}")
        run = await session.get(Run, run_id)
        if not run:
            raise ValueError(f"Run id {run_id} not found")

        # Fetch related objects using await
        logger.info(f"Fetching related objects for run {run_id}")
        hazard: Hazard | None = await session.get(Hazard, run.hazard_id)
        mapping_set: MappingSet | None = await session.get(MappingSet, run.mapping_set_id)
        building_ds: BuildingDataset | None = await session.get(BuildingDataset, run.building_dataset_id)
        if not all([hazard, mapping_set, building_ds]):
            raise ValueError("Run has invalid foreign keys")

        # NEW: Fetch interventions for this run
        logger.info(f"Fetching interventions for run {run_id}")
        interventions_result = await session.execute(
            select(RunIntervention)
            .where(RunIntervention.run_id == run_id)
            .options(joinedload(RunIntervention.intervention))
        )
        run_interventions = interventions_result.scalars().all()
        logger.info(f"Found {len(run_interventions)} interventions for run {run_id}")

        # NEW: Fetch all buildings with asset values for this dataset
        logger.info(f"Fetching buildings for dataset {building_ds.id}")
        buildings_result = await session.execute(
            select(Building).where(Building.dataset_id == building_ds.id)
        )
        buildings = buildings_result.scalars().all()
        logger.info(f"Found {len(buildings)} buildings in dataset {building_ds.id}")
        
        # Create a map of building GUID to asset value
        building_assets = {}
        for building in buildings:
            if building.asset_value is not None:
                building_assets[building.guid] = building.asset_value
        logger.info(f"Found {len(building_assets)} buildings with asset values")

        # Build a map of building_id -> elevation adjustment
        elevation_adjustments = {}
        for ri in run_interventions:
            if ri.intervention.type == 'building_elevation':
                elevation_ft = ri.parameters.get('elevation_ft', 0)
                elevation_adjustments[str(ri.building_id)] = elevation_ft

        logger.info(f"Updating run {run_id} status to RUNNING")
        run.status = "RUNNING"
        session.add(run)
        await session.commit()

        try:
            # File I/O remains synchronous for now
            logger.info(f"Loading mapping set from {mapping_set.json_path}")
            with open(mapping_set.json_path, "r") as f:
                mapping_json = json.load(f)
            arch_to_fragility = _create_mapping_dict(mapping_json)
            logger.info(f"Created mapping dictionary with {len(arch_to_fragility)} entries")

            # Build fragility cache from DB curves
            logger.info("Building fragility cache")
            fragility_cache: Dict[str, Dict[str, Any]] = {}
            # Use await for execute
            result = await session.execute(select(FragilityCurve))
            curves = result.scalars().all()
            logger.info(f"Found {len(curves)} fragility curves")
            for c in curves:
                obj = json.load(open(c.json_path, "r"))
                fragility_cache[obj["id"]] = obj
            logger.info(f"Built fragility cache with {len(fragility_cache)} entries")

            # Ensure all fragility ids referenced in mapping exist
            missing_ids = [fid for fid in arch_to_fragility.values() if fid not in fragility_cache]
            if missing_ids:
                raise ValueError(f"Missing fragility curve(s) in DB: {missing_ids}")

            # Load WSE raster (sync)
            logger.info(f"Loading WSE raster from {hazard.wse_raster_path}")
            wse_ds = rasterio.open(hazard.wse_raster_path)
            logger.info(f"WSE raster loaded: {wse_ds.width}x{wse_ds.height}")

            # Extract buildings from zip (sync)
            logger.info(f"Extracting buildings from {building_ds.shp_path}")
            with TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(building_ds.shp_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)

                # Find .shp file recursively (sync)
                shp_files = list(Path(tmpdir).rglob("*.shp")) # Use rglob
                if not shp_files:
                    raise FileNotFoundError("No .shp file found anywhere in uploaded building dataset zip")
                # Optional: Add check if multiple .shp files are found, decide which to use
                if len(shp_files) > 1:
                    logger.warning(f"Multiple .shp files found, using {shp_files[0]}")
                    
                logger.info(f"Reading buildings from {shp_files[0]}")
                buildings_gdf = gpd.read_file(shp_files[0])
                logger.info(f"Loaded {len(buildings_gdf)} buildings from shapefile")

            # Iterate buildings and compute probabilities (calculations are sync)
            logger.info("Starting building analysis")
            features = []
            for i, (_, b) in enumerate(buildings_gdf.iterrows()):
                if i % 10 == 0:  # Log progress every 10 buildings
                    logger.info(f"Processing building {i+1}/{len(buildings_gdf)}")
                    
                try:
                    guid = b.get('guid') or b.get('id') or _
                    arch_val = int(b['arch_flood']) if 'arch_flood' in b and not pd.isna(b['arch_flood']) else None
                    ffe_ft = float(b['ffe_elev']) if 'ffe_elev' in b and not pd.isna(b['ffe_elev']) else None
                    geom = b.geometry

                    if arch_val is None or ffe_ft is None or geom is None or geom.is_empty:
                        raise ValueError("Missing required attributes or geometry")

                    # NEW: Apply elevation intervention if exists
                    elevation_adjustment = elevation_adjustments.get(str(guid), 0)
                    original_ffe_ft = ffe_ft
                    ffe_ft += elevation_adjustment  # Add intervention elevation

                    # Sample raster (sync rasterio)
                    x, y = geom.x, geom.y
                    row, col = wse_ds.index(x, y)
                    # Clamp to edges if within 1 pixel
                    row = max(0, min(row, wse_ds.height - 1))
                    col = max(0, min(col, wse_ds.width - 1))
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
                    p_ls0 = ls.get('LS_0', 0.0)
                    p_ls1 = ls.get('LS_1', 0.0)
                    p_ls2 = ls.get('LS_2', 0.0)

                    p_ds3 = max(0.0, p_ls2)
                    p_ds2 = max(0.0, p_ls1 - p_ls2)
                    p_ds1 = max(0.0, p_ls0 - p_ls1)
                    p_ds0 = max(0.0, 1.0 - p_ls0)

                    total = p_ds0 + p_ds1 + p_ds2 + p_ds3
                    if not math.isclose(total, 1.0, rel_tol=1e-3):
                        raise ValueError(f"Probabilities do not sum to 1: {total}")

                    features.append({
                        "type": "Feature",
                        "geometry": mapping(geom),
                        "properties": {
                            "guid": str(guid),  # NEW: Include GUID for tracking
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
                            "elevation_adjustment": elevation_adjustment,  # NEW
                            "original_ffe_m": (original_ffe_ft * FT_TO_M) if original_ffe_ft is not None else None,  # NEW
                            "asset_value": building_assets.get(str(guid)),  # NEW: Add asset value
                        }
                    })
                except Exception as point_error:
                    logger.warning(f"Error processing building {i}: {point_error}")
                    guid = b.get('guid') or b.get('id') or _
                    features.append({
                        "type": "Feature",
                        "geometry": mapping(geom) if geom and not geom.is_empty else None,
                        "properties": {
                            "guid": str(guid),
                            "error": str(point_error),
                            "asset_value": building_assets.get(str(guid)),  # NEW: Add asset value even for error cases
                        }
                    })

            logger.info(f"Completed building analysis. Generated {len(features)} features")

            # Create GeoJSON FeatureCollection (sync)
            results_fc = {
                "type": "FeatureCollection",
                "features": features
            }

            # Write results (sync)
            logger.info(f"Writing results to {results_path}")
            with open(results_path, "w") as f:
                json.dump(results_fc, f)
            logger.info(f"Results written to {results_path}")

            # Calculate EAL if we have building asset values
            total_eal = None
            buildings_analyzed = 0
            buildings_with_values = 0
            total_asset_value = 0.0
            
            if building_assets:
                try:
                    logger.info(f"Calculating EAL for run {run_id} with {len(building_assets)} buildings with asset values")
                    
                    # Use await here since calculate_eal is async
                    eal_results = await calculate_eal(run_id, building_assets)
                    
                    total_eal = eal_results.get('total_eal', 0)
                    buildings_analyzed = eal_results.get('building_count', 0)
                    buildings_with_values = len(building_assets)
                    total_asset_value = sum(building_assets.values())
                    
                    logger.info(f"EAL calculation complete: Total EAL = ${total_eal:,.2f}")
                except Exception as e:
                    logger.error(f"Failed to calculate EAL for run {run_id}: {e}")
                    # Don't fail the whole run if EAL calculation fails

            # Update Run status in DB
            logger.info(f"Updating run {run_id} status to COMPLETED")
            run.status = "COMPLETED"
            run.result_path = str(results_path)
            run.finished_at = datetime.utcnow()
            run.total_eal = total_eal
            run.buildings_analyzed = buildings_analyzed
            run.buildings_with_values = buildings_with_values
            run.total_asset_value = total_asset_value
            session.add(run)
            
            # Explicitly commit the final changes
            await session.commit()
            logger.info(f"Successfully completed analysis for run {run_id}")
            
        finally:
            # Ensure raster dataset is closed (important!)
            if 'wse_ds' in locals() and wse_ds:
                wse_ds.close()
                logger.info("WSE raster dataset closed")

    except Exception as e:
        logger.error(f"Error in perform_analysis for run {run_id}: {e}", exc_info=True)
        # Update run status to failed if we can
        try:
            run = await session.get(Run, run_id)
            if run:
                run.status = "FAILED"
                run.finished_at = datetime.utcnow()
                session.add(run)
                await session.commit()
                logger.info(f"Updated run {run_id} status to FAILED")
        except Exception as commit_error:
            logger.error(f"Failed to update run status to FAILED: {commit_error}")
        raise
