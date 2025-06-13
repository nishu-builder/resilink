import logging
from typing import List, Optional
from pathlib import Path

from app.api.interventions import RunInterventionResponse
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.db import get_async_session
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


from app.models import Run, Hazard, MappingSet, BuildingDataset, RunIntervention, RunGroup, ModifiedHazard
from app.services.analysis import perform_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["Runs"])


class RunInterventionCreate(BaseModel):
    building_id: str
    intervention_id: int
    parameters: dict
    cost: Optional[float] = None


class CreateRunRequest(BaseModel):
    name: str
    hazard_id: Optional[int] = None  # Original hazard
    modified_hazard_id: Optional[int] = None  # Modified hazard (from intervention)
    mapping_set_id: int
    building_dataset_id: int
    run_group_id: Optional[int] = None
    interventions: Optional[List[RunInterventionCreate]] = None


class CreateRunGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None


@router.post("/groups", response_model=RunGroup)
async def create_run_group(
    request: CreateRunGroupRequest,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new run group for comparing scenarios."""
    run_group = RunGroup(
        name=request.name,
        description=request.description
    )
    session.add(run_group)
    await session.commit()
    await session.refresh(run_group)
    return run_group


@router.get("/groups", response_model=List[RunGroup])
async def list_run_groups(*, session: AsyncSession = Depends(get_async_session)):
    """List all run groups."""
    result = await session.execute(select(RunGroup))
    groups = result.scalars().all()
    return groups


@router.get("/groups/{group_id}", response_model=RunGroup)
async def get_run_group(
    group_id: int,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    """Get a specific run group."""
    group = await session.get(RunGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Run group not found")
    return group


@router.post("", response_model=Run)
async def create_run(
    request: CreateRunRequest,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    logger.info('Creating new run')
    
    # Validate that either hazard_id or modified_hazard_id is provided, but not both
    if not request.hazard_id and not request.modified_hazard_id:
        raise HTTPException(status_code=400, detail="Either hazard_id or modified_hazard_id must be provided")
    
    if request.hazard_id and request.modified_hazard_id:
        raise HTTPException(status_code=400, detail="Cannot specify both hazard_id and modified_hazard_id")
    
    # Validate the hazard (original or modified)
    hazard = None
    modified_hazard = None
    
    if request.hazard_id:
        hazard = await session.get(Hazard, request.hazard_id)
        if not hazard:
            raise HTTPException(status_code=400, detail="Invalid hazard_id")
    
    if request.modified_hazard_id:
        modified_hazard = await session.get(ModifiedHazard, request.modified_hazard_id)
        if not modified_hazard:
            raise HTTPException(status_code=400, detail="Invalid modified_hazard_id")
        # Get the original hazard for analysis pipeline
        hazard = await session.get(Hazard, modified_hazard.original_hazard_id)
    
    # Validate other required resources
    mapping_set = await session.get(MappingSet, request.mapping_set_id)
    building_dataset = await session.get(BuildingDataset, request.building_dataset_id)

    if not all([hazard, mapping_set, building_dataset]):
        raise HTTPException(status_code=400, detail="Invalid FK id(s)")

    if request.run_group_id:
        run_group = await session.get(RunGroup, request.run_group_id)
        if not run_group:
            raise HTTPException(status_code=400, detail="Invalid run_group_id")

    run = Run(
        name=request.name,
        hazard_id=request.hazard_id,  # Can be None if using modified hazard
        modified_hazard_id=request.modified_hazard_id,  # Can be None if using original hazard
        mapping_set_id=mapping_set.id,
        building_dataset_id=building_dataset.id,
        run_group_id=request.run_group_id,
        status="QUEUED",
    )
    session.add(run)
    await session.commit()

    if request.interventions:
        for intervention_data in request.interventions:
            run_intervention = RunIntervention(
                run_id=run.id,
                **intervention_data.dict()
            )
            session.add(run_intervention)
        await session.commit()

    await session.refresh(run)

    await perform_analysis(run.id)

    await session.refresh(run)
    return run


@router.get("", response_model=List[Run])
async def list_runs(*, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(Run))
    runs = result.scalars().all()
    return runs


@router.get("/{run_id}", response_model=Run)
async def get_run(
    run_id: int,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/results")
async def get_run_results(
    run_id: int,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if not run.result_path:
        raise HTTPException(status_code=404, detail="Results not available for this run.")

    results_file = Path(run.result_path)
    if not results_file.is_file():
         logger.error(f"Result file not found at path: {run.result_path}")
         raise HTTPException(status_code=404, detail="Result file not found on server.")
    
    return FileResponse(results_file, media_type='application/geo+json', filename=results_file.name)


@router.post("/{run_id}/interventions", response_model=RunInterventionResponse)
async def add_run_intervention(
    run_id: int,
    intervention: RunInterventionCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Add an intervention to a run."""
    db_intervention = RunIntervention(
        run_id=run_id,
        **intervention.dict()
    )
    session.add(db_intervention)
    await session.commit()
    await session.refresh(db_intervention)
    return db_intervention


@router.get("/{run_id}/interventions", response_model=List[RunInterventionResponse])
async def list_run_interventions(
    run_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """List all interventions for a specific run."""
    result = await session.execute(
        select(RunIntervention).where(RunIntervention.run_id == run_id)
    )
    interventions = result.scalars().all()
    return interventions
