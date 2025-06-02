from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import get_async_session
from app.models import Intervention, RunIntervention

router = APIRouter(prefix="/interventions", tags=["Interventions"])

class InterventionCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None

class InterventionResponse(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class RunInterventionCreate(BaseModel):
    building_id: str
    intervention_id: int
    parameters: dict
    cost: Optional[float] = None

class RunInterventionResponse(BaseModel):
    id: int
    run_id: int
    building_id: str
    intervention_id: int
    parameters: dict
    cost: Optional[float] = None

    class Config:
        from_attributes = True

@router.post("", response_model=InterventionResponse)
async def create_intervention(
    intervention: InterventionCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new intervention type."""
    db_intervention = Intervention(**intervention.dict())
    session.add(db_intervention)
    await session.commit()
    await session.refresh(db_intervention)
    return db_intervention

@router.get("", response_model=List[InterventionResponse])
async def list_interventions(
    session: AsyncSession = Depends(get_async_session)
):
    """List all available intervention types."""
    result = await session.execute(select(Intervention))
    interventions = result.scalars().all()
    return interventions

@router.get("/{intervention_id}", response_model=InterventionResponse)
async def get_intervention(
    intervention_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """Get a specific intervention type."""
    intervention = await session.get(Intervention, intervention_id)
    if not intervention:
        raise HTTPException(status_code=404, detail="Intervention not found")
    return intervention
