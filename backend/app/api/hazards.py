from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hazard
from app.db import get_async_session
from app.api.utils import handle_data_upload, validate_hazard_file

# Disable automatic trailing slash redirects for this router
router = APIRouter(prefix="/datasets/hazards", tags=["Hazards"], redirect_slashes=False)

DATA_DIR = Path("/data")  # mounted volume in docker-compose; adjust via env later


# Make the route async and use get_async_session
@router.post("/", response_model=Hazard)
async def create_hazard(
    name: str = Form(...),
    wse_raster: UploadFile = File(...),
    *,
    _: AsyncSession = Depends(get_async_session),
):
    # Use await when calling the async utility function
    return await handle_data_upload(
        upload_file=wse_raster,
        name=name,
        model_cls=Hazard,
        path_field_name="wse_raster_path",
        file_prefix="hazard_",
        validation_func=validate_hazard_file,
    )


@router.get("/", response_model=List[Hazard])
async def list_hazards(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Hazard))
    hazards = result.scalars().all()
    return hazards
