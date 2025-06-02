from typing import List
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import geopandas as gpd
from shapely.geometry import mapping
from pydantic import BaseModel

from app.db import get_async_session
from app.models import BuildingDataset, Building

from app.api.utils import handle_data_upload, validate_building_file

router = APIRouter(prefix="/datasets/buildings", tags=["Building Datasets"], redirect_slashes=False)


class AssetValueUpdate(BaseModel):
    asset_value: float


async def extract_buildings_from_shapefile(dataset: BuildingDataset, db: AsyncSession):
    """Extract buildings from shapefile and store them in the database."""
    with TemporaryDirectory() as tmpdir:
        # Extract the zip file
        with zipfile.ZipFile(dataset.shp_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        
        # Find .shp file recursively
        shp_files = list(Path(tmpdir).rglob("*.shp"))
        if not shp_files:
            raise ValueError("No .shp file found in uploaded building dataset zip")
        
        # Read the shapefile
        buildings_gdf = gpd.read_file(shp_files[0])
        
        # Extract and store each building
        buildings = []
        for idx, row in buildings_gdf.iterrows():
            # Get building ID (try different possible field names)
            guid = str(row.get('guid') or row.get('id') or row.get('OBJECTID') or idx)
            
            # Convert geometry to GeoJSON format
            geometry = mapping(row.geometry) if row.geometry is not None else None
            
            # Extract all properties (excluding geometry)
            properties = row.drop('geometry').to_dict() if 'geometry' in row else row.to_dict()
            
            # Create Building object
            building = Building(
                guid=guid,
                dataset_id=dataset.id,
                geometry=geometry,
                properties=properties,
                asset_value=None  # Will be set by user later
            )
            buildings.append(building)
        
        # Bulk insert buildings
        db.add_all(buildings)
        await db.commit()
        
        # Update dataset with feature count
        dataset.feature_count = len(buildings)
        db.add(dataset)
        await db.commit()
        
        return len(buildings)


@router.post("", response_model=BuildingDataset)
async def create_building_dataset(
    name: str = Form(...),
    shapefile_zip: UploadFile = File(...),
    *,
    db: AsyncSession = Depends(get_async_session)
):
    # First, handle the file upload and create the dataset record
    dataset = await handle_data_upload(
        upload_file=shapefile_zip,
        name=name,
        model_cls=BuildingDataset,
        path_field_name="shp_path",
        file_prefix="building_",
        validation_func=validate_building_file,
    )
    
    # Extract and store buildings
    try:
        building_count = await extract_buildings_from_shapefile(dataset, db)
    except Exception as e:
        # If extraction fails, delete the dataset and raise error
        await db.delete(dataset)
        await db.commit()
        raise HTTPException(status_code=422, detail=f"Failed to extract buildings: {str(e)}")
    
    return dataset


@router.get("", response_model=List[BuildingDataset])
async def list_datasets(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(BuildingDataset))
    datasets = result.scalars().all()
    return datasets


@router.get("/{dataset_id}", response_model=BuildingDataset)
async def get_dataset(
    dataset_id: int,
    *,
    db: AsyncSession = Depends(get_async_session)
):
    """Get a single building dataset by ID."""
    result = await db.execute(
        select(BuildingDataset).where(BuildingDataset.id == dataset_id)
    )
    dataset = result.scalar_one_or_none()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Building dataset not found")
    
    return dataset


@router.get("/{dataset_id}/buildings", response_model=List[Building])
async def list_buildings(
    dataset_id: int,
    *,
    db: AsyncSession = Depends(get_async_session)
):
    """List all buildings in a dataset."""
    result = await db.execute(
        select(Building).where(Building.dataset_id == dataset_id)
    )
    buildings = result.scalars().all()
    return buildings


@router.post("/{dataset_id}/buildings/{building_guid}")
async def update_building_asset_value(
    dataset_id: int,
    building_guid: str,
    update_data: AssetValueUpdate,
    *,
    db: AsyncSession = Depends(get_async_session)
):
    """Update the asset value for a specific building."""
    result = await db.execute(
        select(Building)
        .where(Building.dataset_id == dataset_id)
        .where(Building.guid == building_guid)
    )
    building = result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    building.asset_value = update_data.asset_value
    db.add(building)
    await db.commit()
    await db.refresh(building)
    
    return building


@router.post("/{dataset_id}/buildings/bulk-update-assets")
async def bulk_update_asset_values(
    dataset_id: int,
    updates: dict[str, float],  # {building_guid: asset_value}
    *,
    db: AsyncSession = Depends(get_async_session)
):
    """Bulk update asset values for multiple buildings."""
    # Get all buildings for this dataset
    result = await db.execute(
        select(Building).where(Building.dataset_id == dataset_id)
    )
    buildings = result.scalars().all()
    
    # Create a map for quick lookup
    building_map = {b.guid: b for b in buildings}
    
    # Update asset values
    updated_count = 0
    for guid, asset_value in updates.items():
        if guid in building_map:
            building_map[guid].asset_value = asset_value
            db.add(building_map[guid])
            updated_count += 1
    
    await db.commit()
    
    return {"updated": updated_count, "total_requested": len(updates)}
