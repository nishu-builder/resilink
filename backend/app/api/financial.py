from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, Any
from pydantic import BaseModel

from app.db import get_async_session
from app.models import RunIntervention
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
    # TODO: Get actual building values from database
    # For now, use mock values
    building_values = {f"B{i:03d}": 1_000_000 + i * 100_000 for i in range(1, 20)}

    try:
        eal_results = await calculate_eal(run_id, building_values)
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

    # Mock building values
    building_values = {f"B{i:03d}": 1_000_000 + i * 100_000 for i in range(1, 20)}

    try:
        # Calculate EAL for both runs
        eal1 = await calculate_eal(request.run_id_1, building_values)
        eal2 = await calculate_eal(request.run_id_2, building_values)
        
        # Determine which run has lower EAL (better outcome)
        if eal1['total_eal'] > eal2['total_eal']:
            # Run 2 is better
            baseline_eal = eal1['total_eal']
            improved_eal = eal2['total_eal']
            incremental_cost = total_cost2 - total_cost1
        else:
            # Run 1 is better or same
            baseline_eal = eal2['total_eal']
            improved_eal = eal1['total_eal']
            incremental_cost = total_cost1 - total_cost2
        
        eal_reduction = baseline_eal - improved_eal
        
        # Calculate ROI if there's a cost difference
        roi = eal_reduction / abs(incremental_cost) if incremental_cost != 0 else float('inf')
        
        return {
            "run_1": {
                "id": request.run_id_1,
                "eal": eal1['total_eal'],
                "intervention_cost": total_cost1
            },
            "run_2": {
                "id": request.run_id_2,
                "eal": eal2['total_eal'],
                "intervention_cost": total_cost2
            },
            "comparison": {
                "eal_reduction": eal_reduction,
                "eal_reduction_percent": (eal_reduction / baseline_eal * 100) if baseline_eal > 0 else 0,
                "incremental_cost": incremental_cost,
                "roi": roi,
                "payback_years": abs(incremental_cost) / eal_reduction if eal_reduction > 0 else float('inf')
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 