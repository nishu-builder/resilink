from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import BuildingDataset

from app.api.utils import handle_data_upload, validate_building_file

router = APIRouter(prefix="/datasets/buildings", tags=["Building Datasets"], redirect_slashes=False)


@router.post("/", response_model=BuildingDataset)
async def create_building_dataset(
    name: str = Form(...),
    shapefile_zip: UploadFile = File(...),
    *,
    _: AsyncSession = Depends(get_async_session)
):
    return await handle_data_upload(
        upload_file=shapefile_zip,
        name=name,
        model_cls=BuildingDataset,
        path_field_name="shp_path",
        file_prefix="building_",
        validation_func=validate_building_file,
    )


@router.get("/", response_model=List[BuildingDataset])
async def list_datasets(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(BuildingDataset))
    datasets = result.scalars().all()
    return datasets 