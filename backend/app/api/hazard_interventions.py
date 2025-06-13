from pathlib import Path
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models import HazardIntervention, Hazard, ModifiedHazard
from app.db import get_async_session

router = APIRouter(prefix="/hazard-interventions", tags=["Hazard Interventions"])


class HazardInterventionCreate(BaseModel):
    name: str
    type: str  # "dam" or "levee"
    hazard_id: int
    geometry: dict  # GeoJSON
    parameters: dict
    

class HazardInterventionResponse(BaseModel):
    id: int
    name: str
    type: str
    hazard_id: int
    geometry: dict
    parameters: dict
    created_at: str
    

@router.post("", response_model=HazardInterventionResponse)
async def create_hazard_intervention(
    intervention: HazardInterventionCreate,
    db: AsyncSession = Depends(get_async_session)
):
    """Create a new hazard-level intervention (dam or levee)."""
    # Validate hazard exists
    hazard = await db.get(Hazard, intervention.hazard_id)
    if not hazard:
        raise HTTPException(404, "Hazard not found")
    
    # Validate intervention type
    if intervention.type not in ["dam", "levee"]:
        raise HTTPException(400, "Intervention type must be 'dam' or 'levee'")
    
    # Validate geometry is valid GeoJSON
    if "type" not in intervention.geometry or "coordinates" not in intervention.geometry:
        raise HTTPException(400, "Invalid GeoJSON geometry")
    
    # Validate parameters based on type
    if intervention.type == "dam":
        required_params = ["height", "width", "crest_elevation"]
        for param in required_params:
            if param not in intervention.parameters:
                raise HTTPException(400, f"Missing required dam parameter: {param}")
    elif intervention.type == "levee":
        required_params = ["height", "top_width"]
        for param in required_params:
            if param not in intervention.parameters:
                raise HTTPException(400, f"Missing required levee parameter: {param}")
    
    # Create intervention
    db_intervention = HazardIntervention(
        name=intervention.name,
        type=intervention.type,
        hazard_id=intervention.hazard_id,
        geometry=intervention.geometry,
        parameters=intervention.parameters
    )
    
    db.add(db_intervention)
    await db.commit()
    await db.refresh(db_intervention)
    
    return HazardInterventionResponse(
        id=db_intervention.id,
        name=db_intervention.name,
        type=db_intervention.type,
        hazard_id=db_intervention.hazard_id,
        geometry=db_intervention.geometry,
        parameters=db_intervention.parameters,
        created_at=db_intervention.created_at.isoformat()
    )


@router.get("", response_model=List[HazardInterventionResponse])
async def list_hazard_interventions(
    hazard_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_session)
):
    """List all hazard interventions, optionally filtered by hazard."""
    query = select(HazardIntervention)
    if hazard_id:
        query = query.where(HazardIntervention.hazard_id == hazard_id)
    
    result = await db.execute(query)
    interventions = result.scalars().all()
    
    return [
        HazardInterventionResponse(
            id=i.id,
            name=i.name,
            type=i.type,
            hazard_id=i.hazard_id,
            geometry=i.geometry,
            parameters=i.parameters,
            created_at=i.created_at.isoformat()
        )
        for i in interventions
    ]


@router.get("/{intervention_id}", response_model=HazardInterventionResponse)
async def get_hazard_intervention(
    intervention_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific hazard intervention."""
    intervention = await db.get(HazardIntervention, intervention_id)
    if not intervention:
        raise HTTPException(404, "Intervention not found")
    
    return HazardInterventionResponse(
        id=intervention.id,
        name=intervention.name,
        type=intervention.type,
        hazard_id=intervention.hazard_id,
        geometry=intervention.geometry,
        parameters=intervention.parameters,
        created_at=intervention.created_at.isoformat()
    )


@router.post("/{intervention_id}/apply")
async def apply_hazard_intervention(
    intervention_id: int,
    background_tasks: BackgroundTasks,
    model_type: str = "anuga",  # or "landlab"
    db: AsyncSession = Depends(get_async_session)
):
    """Apply intervention and generate modified hazard using hydraulic modeling."""
    intervention = await db.get(HazardIntervention, intervention_id)
    if not intervention:
        raise HTTPException(404, "Intervention not found")
    
    # Queue hydraulic modeling task
    background_tasks.add_task(
        process_intervention_with_hydraulic_model,
        intervention_id=intervention_id,
        model_type=model_type,
        db=db
    )
    
    return {
        "status": "processing",
        "intervention_id": intervention_id,
        "model_type": model_type,
        "message": "Hydraulic modeling started. This may take several minutes."
    }


async def process_intervention_with_hydraulic_model(
    intervention_id: int,
    model_type: str,
    db: AsyncSession
):
    """Process intervention using ANUGA or Landlab."""
    # This is a placeholder - actual implementation would:
    # 1. Load the original hazard raster
    # 2. Set up ANUGA or Landlab model
    # 3. Add intervention geometry (dam/levee)
    # 4. Run hydraulic simulation
    # 5. Export modified WSE raster
    # 6. Save to ModifiedHazard table
    
    # For now, we'll create a stub modified hazard
    intervention = await db.get(HazardIntervention, intervention_id, {"hazard"})
    
    modified_hazard = ModifiedHazard(
        name=f"{intervention.name} - Modified Hazard",
        original_hazard_id=intervention.hazard_id,
        intervention_id=intervention_id,
        wse_raster_path=intervention.hazard.wse_raster_path,  # Placeholder - would be new raster
        model_type=model_type,
        model_output_path=f"/data/models/{model_type}_{intervention_id}"
    )
    
    db.add(modified_hazard)
    await db.commit()


@router.get("/{intervention_id}/modified-hazards")
async def get_modified_hazards(
    intervention_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get all modified hazards generated from this intervention."""
    query = select(ModifiedHazard).where(
        ModifiedHazard.intervention_id == intervention_id
    )
    result = await db.execute(query)
    modified_hazards = result.scalars().all()
    
    return [
        {
            "id": mh.id,
            "name": mh.name,
            "model_type": mh.model_type,
            "created_at": mh.created_at.isoformat(),
            "wse_raster_path": mh.wse_raster_path
        }
        for mh in modified_hazards
    ]