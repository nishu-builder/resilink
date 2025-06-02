from typing import List
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FragilityCurve
from app.db import get_async_session

from .utils import handle_data_upload, validate_fragility_file

router = APIRouter(prefix="/datasets/fragilities", tags=["Fragility Curves"], redirect_slashes=False)

@router.post("/", response_model=FragilityCurve)
async def create_fragility_curve(
    name: str = Form(...),
    fragility_json: UploadFile = File(...),
    *,
    _: AsyncSession = Depends(get_async_session),
):
    return await handle_data_upload(
        upload_file=fragility_json,
        name=name,
        model_cls=FragilityCurve,
        path_field_name="json_path",
        file_prefix="fragility_",
        validation_func=validate_fragility_file,
    )

@router.post("/batch", response_model=List[FragilityCurve], status_code=201)
async def create_fragility_curves_batch(
    fragility_files: List[UploadFile] = File(...),
    *,
    _: AsyncSession = Depends(get_async_session),
):
    """Handles uploading multiple fragility JSON files at once."""
    created_curves = []
    for upload_file in fragility_files:
        derived_name = Path(upload_file.filename).stem if upload_file.filename else "unknown_fragility"
        curve = await handle_data_upload(
            upload_file=upload_file,
            name=derived_name,
            model_cls=FragilityCurve,
            path_field_name="json_path",
            file_prefix="fragility_",
            validation_func=validate_fragility_file,
        )
        created_curves.append(curve)
    
    return created_curves

@router.get("/", response_model=List[FragilityCurve])
async def list_curves(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(FragilityCurve))
    curves = result.scalars().all()
    return curves 