from typing import Dict, List, Optional, Any
import json
from pathlib import Path

# Damage ratios by damage state (simplified - should come from configuration)
DAMAGE_RATIOS = {
    "DS0": 0.0,    # No damage
    "DS1": 0.02,   # Slight damage - 2% of building value
    "DS2": 0.10,   # Moderate damage - 10% of building value
    "DS3": 0.50,   # Substantial damage - 50% of building value
}

async def calculate_eal(run_id: int, building_values: Dict[str, float]) -> Dict[str, Any]:
    """Calculate Expected Annual Loss for a run."""
    results_path = Path("/data") / f"results_{run_id}.geojson"

    if not results_path.exists():
        raise FileNotFoundError(f"Results not found for run {run_id}")

    with open(results_path) as f:
        results = json.load(f)

    total_eal = 0
    building_eals = {}
    building_details = []

    for feature in results['features']:
        props = feature['properties']
        building_id = props.get('guid')
        
        # Skip features with errors
        if 'error' in props:
            # Still include error buildings in details for completeness
            if building_id:
                building_details.append({
                    "building_id": building_id,
                    "asset_value": building_values.get(building_id, 0),
                    "damage_states": {
                        "P_DS0": None,
                        "P_DS1": None,
                        "P_DS2": None,
                        "P_DS3": None
                    },
                    "expected_damage_cost": 0,
                    "error": props.get('error')
                })
            continue

        # Skip buildings that don't have asset values
        if building_id not in building_values:
            continue

        # Get probabilities
        p_ds0 = props.get('P_DS0', 0)
        p_ds1 = props.get('P_DS1', 0)
        p_ds2 = props.get('P_DS2', 0)
        p_ds3 = props.get('P_DS3', 0)

        # Get building value
        building_value = building_values[building_id]

        # Calculate EAL for this building
        building_eal = (
            p_ds0 * DAMAGE_RATIOS['DS0'] * building_value +
            p_ds1 * DAMAGE_RATIOS['DS1'] * building_value +
            p_ds2 * DAMAGE_RATIOS['DS2'] * building_value +
            p_ds3 * DAMAGE_RATIOS['DS3'] * building_value
        )

        building_eals[building_id] = building_eal
        total_eal += building_eal

        # Add detailed building information
        building_details.append({
            "building_id": building_id,
            "asset_value": building_value,
            "damage_states": {
                "P_DS0": round(p_ds0, 4),
                "P_DS1": round(p_ds1, 4),
                "P_DS2": round(p_ds2, 4),
                "P_DS3": round(p_ds3, 4)
            },
            "expected_damage_cost": round(building_eal, 2),
            "damage_costs_by_state": {
                "DS0": round(DAMAGE_RATIOS['DS0'] * building_value, 2),
                "DS1": round(DAMAGE_RATIOS['DS1'] * building_value, 2),
                "DS2": round(DAMAGE_RATIOS['DS2'] * building_value, 2),
                "DS3": round(DAMAGE_RATIOS['DS3'] * building_value, 2)
            }
        })

    return {
        "total_eal": total_eal,
        "building_eals": building_eals,
        "building_count": len(building_eals),
        "building_details": building_details
    }

async def calculate_intervention_roi(
    baseline_run_id: int,
    intervention_run_id: int,
    building_values: Dict[str, float],
    intervention_costs: float
) -> Dict[str, float]:
    """Calculate ROI for interventions."""

    baseline_eal = await calculate_eal(baseline_run_id, building_values)
    intervention_eal = await calculate_eal(intervention_run_id, building_values)

    eal_reduction = baseline_eal['total_eal'] - intervention_eal['total_eal']

    # Simple ROI calculation (annual benefit / one-time cost)
    # In reality, would use NPV with discount rate
    roi = eal_reduction / intervention_costs if intervention_costs > 0 else 0

    return {
        "baseline_eal": baseline_eal['total_eal'],
        "intervention_eal": intervention_eal['total_eal'],
        "eal_reduction": eal_reduction,
        "eal_reduction_percent": (eal_reduction / baseline_eal['total_eal'] * 100) if baseline_eal['total_eal'] > 0 else 0,
        "intervention_cost": intervention_costs,
        "roi": roi,
        "payback_years": intervention_costs / eal_reduction if eal_reduction > 0 else None
    } 