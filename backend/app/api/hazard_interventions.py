from typing import List, Optional

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
    """Process intervention using hydraulic modeling."""
    from app.services.hydraulic_modeling import process_intervention_modeling
    import asyncio
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get intervention
        intervention = await db.get(HazardIntervention, intervention_id)
        
        if not intervention:
            logger.error(f"Intervention {intervention_id} not found")
            return
            
        # Get related hazard
        hazard = await db.get(Hazard, intervention.hazard_id)
        
        if not hazard:
            logger.error(f"Hazard {intervention.hazard_id} not found")
            return
        
        logger.info(f"Processing intervention {intervention_id}: {intervention.name}")
        
        # Prepare file paths
        original_raster = hazard.wse_raster_path
        output_dir = Path(f"/data/models/{model_type}_{intervention_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_raster = str(output_dir / "modified_wse.tif")
        
        # Run hydraulic modeling in thread pool (CPU-intensive)
        loop = asyncio.get_event_loop()
        modeling_results = await loop.run_in_executor(
            None,
            process_intervention_modeling,
            intervention_id,
            original_raster,
            intervention.geometry,
            intervention.type,
            intervention.parameters,
            output_raster
        )
        
        if modeling_results['success']:
            # Create ModifiedHazard record
            modified_hazard = ModifiedHazard(
                name=f"{intervention.name} - Modified Hazard",
                original_hazard_id=intervention.hazard_id,
                intervention_id=intervention_id,
                wse_raster_path=output_raster,
                model_type=model_type,
                model_output_path=str(output_dir),
                model_results=modeling_results  # Store modeling statistics
            )
            
            db.add(modified_hazard)
            await db.commit()
            await db.refresh(modified_hazard)
            
            logger.info(f"Successfully created modified hazard {modified_hazard.id}")
            
        else:
            logger.error(f"Hydraulic modeling failed: {modeling_results.get('error')}")
            
    except Exception as e:
        logger.error(f"Error in hydraulic modeling process: {e}")
        await db.rollback()


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
            "wse_raster_path": mh.wse_raster_path,
            "model_results": mh.model_results,
            "status": mh.model_results.get("success", False) if mh.model_results else False
        }
        for mh in modified_hazards
    ]