from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, Form
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MappingSet
from app.db import get_async_session
from app.api.utils import handle_data_upload, validate_mapping_file

router = APIRouter(prefix="/datasets/mappings", tags=["Mapping Sets"])

DATA_DIR = Path("/data")


@router.post("/", response_model=MappingSet)
async def create_mapping_set(
    name: str = Form(...),
    mapping_json: UploadFile = File(...),
    *,
    _: AsyncSession = Depends(get_async_session),
):
    return await handle_data_upload(
        upload_file=mapping_json,
        name=name,
        model_cls=MappingSet,
        path_field_name="json_path",
        file_prefix="mapping_",
        validation_func=validate_mapping_file,
    )


@router.get("/", response_model=List[MappingSet])
async def list_mappings(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(MappingSet))
    mappings = result.scalars().all()
    return mappings
