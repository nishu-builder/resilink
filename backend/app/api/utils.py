import os
import logging
import zipfile
import json
from pathlib import Path
from typing import TypeVar, Type, Callable

import rasterio
from fastapi import UploadFile, HTTPException
from app.db import get_current_session
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DATA_DIR = Path("/data")  # Centralized data directory path

# Define a TypeVar for the SQLModel subclass
ModelType = TypeVar("ModelType", bound=SQLModel)


# --- Validation Functions ---

def validate_hazard_file(upload_file: UploadFile):
    """Validate hazard raster file (GeoTIFF)."""
    filename = upload_file.filename
    if not filename:
        raise HTTPException(
            status_code=422,
            detail="No name"
        )
    if not filename or not filename.lower().endswith(('.tif', '.tiff')):
        raise HTTPException(
            status_code=422,
            detail="Invalid file type. Only GeoTIFF (.tif, .tiff) files are accepted for hazards."
        )
    try:
        upload_file.file.seek(0)
        with rasterio.open(upload_file.file) as src:
            # Could add more specific checks like CRS here if needed
            pass
        upload_file.file.seek(0)
    except rasterio.RasterioIOError as e:
        raise HTTPException(status_code=422, detail=f"Invalid or corrupt raster file: {e}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to validate raster file: {e}")


def validate_fragility_file(upload_file: UploadFile):
    """Validate fragility JSON file."""
    filename = upload_file.filename
    if not filename or not filename.lower().endswith('.json'):
        raise HTTPException(status_code=422, detail="Invalid file type. Only JSON (.json) files are accepted for fragility curves.")
    try:
        upload_file.file.seek(0)
        data_json = json.load(upload_file.file)
        if "fragilityCurves" not in data_json:
            raise ValueError("Invalid fragility format: Missing 'fragilityCurves' key.")
        # Optional: Extract name/id if needed, though name is passed separately now
        # extracted_name = data_json.get("id")
        upload_file.file.seek(0)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON format.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read or validate JSON file: {e}")


def validate_mapping_file(upload_file: UploadFile):
    """Validate mapping JSON file."""
    filename = upload_file.filename
    if not filename or not filename.lower().endswith('.json'):
        raise HTTPException(status_code=422, detail="Invalid file type. Only JSON (.json) files are accepted for mapping sets.")
    try:
        upload_file.file.seek(0)
        data_json = json.load(upload_file.file)
        if "mappings" not in data_json:
            raise ValueError("Invalid mapping format: Missing 'mappings' key.")
        upload_file.file.seek(0)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON format.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read or validate JSON file: {e}")


def validate_building_file(upload_file: UploadFile):
    """Validate building dataset ZIP file."""
    filename = upload_file.filename
    if not filename or not filename.lower().endswith('.zip'):
        raise HTTPException(status_code=422, detail="Invalid file type. Only ZIP (.zip) archives containing a shapefile are accepted.")
    try:
        upload_file.file.seek(0)
        with zipfile.ZipFile(upload_file.file, 'r') as zf:
            has_shp = any(fname.lower().endswith('.shp') for fname in zf.namelist())
            if not has_shp:
                raise ValueError("The uploaded ZIP archive does not contain a .shp file.")
        upload_file.file.seek(0)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=422, detail="Invalid or corrupt ZIP file.")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to read or validate ZIP file: {e}")


# --- Generic Upload Handler ---

async def handle_data_upload(
    *,
    upload_file: UploadFile,
    name: str,
    model_cls: Type[ModelType],
    path_field_name: str,
    file_prefix: str,
    validation_func: Callable[[UploadFile], None],
) -> ModelType:
    """
    Handles common logic for validating, saving, and creating DB record for uploads.

    Args:
        upload_file: The uploaded file object.
        name: The name provided for the dataset.
        session: The database session.
        model_cls: The SQLModel class to instantiate (e.g., Hazard).
        path_field_name: The attribute name on the model for the file path (e.g., "wse_raster_path").
        file_prefix: The prefix for the saved filename (e.g., "hazard_").
        validation_func: The specific validation function to call for the file type.

    Returns:
        The created and refreshed database model instance.

    Raises:
        HTTPException: If validation fails or file saving fails.
    """
    logger.info(f'handle_data_upload: {name} {model_cls} {path_field_name} {file_prefix} {upload_file.filename}')
    DATA_DIR.mkdir(exist_ok=True, parents=True)

    # Perform type-specific validation
    validation_func(upload_file)
    dest_path = DATA_DIR / f"{file_prefix}{name}"

    # Save the validated file
    try:
        # Ensure file pointer is at the beginning after validation reads
        upload_file.file.seek(0)
        with dest_path.open("wb") as dest:
            dest.write(upload_file.file.read())
    except Exception as e:
        # Handle potential file system errors during save
        raise HTTPException(status_code=500, detail=f"Could not save uploaded file: {e}")

    db_model = model_cls(name=name, **{path_field_name: str(dest_path)})
    session = get_current_session()
    session.add(db_model)
    await session.commit()
    await session.refresh(db_model)

    return db_model
