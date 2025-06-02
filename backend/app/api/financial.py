from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, Any
from pydantic import BaseModel

from app.db import get_async_session
from app.models import RunIntervention, Run, Building
from app.services.financial import calculate_eal, calculate_intervention_roi

router = APIRouter(prefix="/financial", tags=["Financial Analysis"])


class CompareRunsRequest(BaseModel):
    run_id_1: int
    run_id_2: int


@router.get("/runs/{run_id}/eal")
async def get_run_eal(
    run_id: int,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """Calculate Expected Annual Loss for a run."""
    # Get the run
    result = await session.execute(
        select(Run).where(Run.id == run_id)
    )
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    # Always recalculate to get building details (since we need detailed info)
    # Fetch all buildings for this dataset with their asset values
    buildings_result = await session.execute(
        select(Building).where(Building.dataset_id == run.building_dataset_id)
    )
    buildings = buildings_result.scalars().all()
    
    # Create building values dict using GUID as key
    building_values = {}
    for building in buildings:
        if building.asset_value is not None and building.asset_value > 0:
            building_values[building.guid] = building.asset_value

    if not building_values:
        raise HTTPException(
            status_code=400, 
            detail="No buildings with asset values found for this run. Please set asset values first."
        )

    try:
        eal_results = await calculate_eal(run_id, building_values)
        eal_results["buildings_with_values"] = len(building_values)
        eal_results["total_asset_value"] = sum(building_values.values())
        
        # Store the calculated values for future use (summary only)
        run.total_eal = eal_results["total_eal"]
        run.buildings_analyzed = eal_results["building_count"]
        run.buildings_with_values = len(building_values)
        run.total_asset_value = sum(building_values.values())
        session.add(run)
        await session.commit()
        
        return eal_results
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare-runs")
async def compare_runs(
    request: CompareRunsRequest,
    session: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """Compare financial metrics between two runs.
    
    This can be used to compare:
    - A baseline run vs an intervention run
    - Two different intervention scenarios
    - Any two runs in general
    """
    # Get both runs
    result1 = await session.execute(select(Run).where(Run.id == request.run_id_1))
    run1 = result1.scalar_one_or_none()
    
    result2 = await session.execute(select(Run).where(Run.id == request.run_id_2))
    run2 = result2.scalar_one_or_none()
    
    if not run1 or not run2:
        raise HTTPException(status_code=404, detail="One or both runs not found")
    
    # Ensure both runs use the same building dataset for fair comparison
    if run1.building_dataset_id != run2.building_dataset_id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot compare runs with different building datasets"
        )
    
    # Fetch buildings with asset values
    buildings_result = await session.execute(
        select(Building).where(Building.dataset_id == run1.building_dataset_id)
    )
    buildings = buildings_result.scalars().all()
    
    building_values = {}
    for building in buildings:
        if building.asset_value is not None and building.asset_value > 0:
            building_values[building.guid] = building.asset_value
    
    if not building_values:
        raise HTTPException(
            status_code=400, 
            detail="No buildings with asset values found. Please set asset values first."
        )
    
    # Get intervention costs for both runs
    result1 = await session.execute(
        select(RunIntervention).where(RunIntervention.run_id == request.run_id_1)
    )
    interventions1 = result1.scalars().all()
    total_cost1 = sum(i.cost or 0 for i in interventions1)
    
    result2 = await session.execute(
        select(RunIntervention).where(RunIntervention.run_id == request.run_id_2)
    )
    interventions2 = result2.scalars().all()
    total_cost2 = sum(i.cost or 0 for i in interventions2)

    try:
        # Get EAL for both runs (uses stored values if available)
        eal1_total = run1.total_eal
        eal2_total = run2.total_eal
        
        # If EAL not stored, calculate it
        if eal1_total is None:
            eal1 = await calculate_eal(request.run_id_1, building_values)
            eal1_total = eal1['total_eal']
        
        if eal2_total is None:
            eal2 = await calculate_eal(request.run_id_2, building_values)
            eal2_total = eal2['total_eal']
        
        # Determine which run has lower EAL (better outcome)
        if eal1_total > eal2_total:
            # Run 2 is better
            baseline_eal = eal1_total
            improved_eal = eal2_total
            incremental_cost = total_cost2 - total_cost1
        else:
            # Run 1 is better or same
            baseline_eal = eal2_total
            improved_eal = eal1_total
            incremental_cost = total_cost1 - total_cost2
        
        eal_reduction = baseline_eal - improved_eal
        
        # Calculate ROI if there's a cost difference
        roi = eal_reduction / abs(incremental_cost) if incremental_cost != 0 else None
        
        # Calculate payback years
        payback_years = abs(incremental_cost) / eal_reduction if eal_reduction > 0 else None
        
        return {
            "run_1": {
                "id": request.run_id_1,
                "eal": eal1_total,
                "intervention_cost": total_cost1
            },
            "run_2": {
                "id": request.run_id_2,
                "eal": eal2_total,
                "intervention_cost": total_cost2
            },
            "comparison": {
                "eal_reduction": eal_reduction,
                "eal_reduction_percent": (eal_reduction / baseline_eal * 100) if baseline_eal > 0 else 0,
                "incremental_cost": incremental_cost,
                "roi": roi,
                "payback_years": payback_years
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 