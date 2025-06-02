import logging
from typing import List
from pathlib import Path
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import FileResponse
from app.db import get_async_session
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel


from app.models import Run, Hazard, MappingSet, BuildingDataset
from app.services.analysis import perform_analysis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["Runs"])


class CreateRunRequest(BaseModel):
    name: str
    hazard_id: int
    mapping_set_id: int
    building_dataset_id: int


@router.post("/", response_model=Run)
async def create_run(
    request: CreateRunRequest,
    *,
    session: AsyncSession = Depends(get_async_session),
):
    logger.info('Hi I am here')
    hazard = await session.get(Hazard, request.hazard_id)
    mapping_set = await session.get(MappingSet, request.mapping_set_id)
    building_dataset = await session.get(BuildingDataset, request.building_dataset_id)

    if not all([hazard, mapping_set, building_dataset]):
        raise HTTPException(status_code=400, detail="Invalid FK id(s)")

    run = Run(
        name=request.name,
        hazard_id=hazard.id,
        mapping_set_id=mapping_set.id,
        building_dataset_id=building_dataset.id,
        status="QUEUED",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    await perform_analysis(run.id)

    await session.refresh(run)
    return run


@router.get("/", response_model=List[Run])
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
