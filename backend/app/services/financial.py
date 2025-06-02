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
    results_path = Path(f"/data/results_{run_id}.geojson")

    if not results_path.exists():
        raise FileNotFoundError(f"Results not found for run {run_id}")

    with open(results_path) as f:
        results = json.load(f)

    total_eal = 0
    building_eals = {}

    for feature in results['features']:
        props = feature['properties']
        building_id = props.get('guid')
        
        # Skip features with errors
        if 'error' in props:
            continue

        # Get probabilities
        p_ds0 = props.get('P_DS0', 0)
        p_ds1 = props.get('P_DS1', 0)
        p_ds2 = props.get('P_DS2', 0)
        p_ds3 = props.get('P_DS3', 0)

        # Get building value (would come from database in real implementation)
        building_value = building_values.get(str(building_id), 1_000_000)  # Default $1M

        # Calculate EAL for this building
        building_eal = (
            p_ds0 * DAMAGE_RATIOS['DS0'] * building_value +
            p_ds1 * DAMAGE_RATIOS['DS1'] * building_value +
            p_ds2 * DAMAGE_RATIOS['DS2'] * building_value +
            p_ds3 * DAMAGE_RATIOS['DS3'] * building_value
        )

        building_eals[building_id] = building_eal
        total_eal += building_eal

    return {
        "total_eal": total_eal,
        "building_eals": building_eals,
        "building_count": len(building_eals)
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
        "payback_years": intervention_costs / eal_reduction if eal_reduction > 0 else float('inf')
    } 