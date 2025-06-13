from pathlib import Path
from typing import List, Optional, Tuple
import io
import json

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import Response, JSONResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from rio_tiler.io import Reader

from app.models import Hazard
from app.db import get_async_session
from app.api.utils import handle_data_upload, validate_hazard_file

# Disable automatic trailing slash redirects for this router
router = APIRouter(prefix="/datasets/hazards", tags=["Hazards"], redirect_slashes=False)

DATA_DIR = Path("/data")  # mounted volume in docker-compose; adjust via env later


# Make the route async and use get_async_session
@router.post("", response_model=Hazard)
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


@router.get("", response_model=List[Hazard])
async def list_hazards(*, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(Hazard))
    hazards = result.scalars().all()
    return hazards


@router.get("/{hazard_id}/info")
async def get_hazard_info(
    hazard_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    """Get metadata and statistics about a hazard raster."""
    hazard = await db.get(Hazard, hazard_id)
    if not hazard:
        raise HTTPException(404, "Hazard not found")
    
    try:
        with rasterio.open(hazard.wse_raster_path) as src:
            bounds = src.bounds
            data = src.read(1, masked=True)
            
            return {
                "id": hazard.id,
                "name": hazard.name,
                "bounds": {
                    "minx": bounds.left,
                    "miny": bounds.bottom,
                    "maxx": bounds.right,
                    "maxy": bounds.top
                },
                "crs": str(src.crs),
                "width": src.width,
                "height": src.height,
                "transform": list(src.transform),
                "statistics": {
                    "min": float(np.nanmin(data)),
                    "max": float(np.nanmax(data)),
                    "mean": float(np.nanmean(data)),
                    "std": float(np.nanstd(data))
                }
            }
    except Exception as e:
        raise HTTPException(500, f"Error reading raster: {str(e)}")


@router.get("/{hazard_id}/preview")
async def get_hazard_preview(
    hazard_id: int,
    width: int = Query(800, description="Preview width in pixels"),
    height: int = Query(600, description="Preview height in pixels"),
    colormap: str = Query("Blues", description="Matplotlib colormap name"),
    db: AsyncSession = Depends(get_async_session)
):
    """Generate a preview image of the hazard raster."""
    hazard = await db.get(Hazard, hazard_id)
    if not hazard:
        raise HTTPException(404, "Hazard not found")
    
    try:
        with rasterio.open(hazard.wse_raster_path) as src:
            # Calculate output dimensions maintaining aspect ratio
            aspect = src.width / src.height
            if width / height > aspect:
                width = int(height * aspect)
            else:
                height = int(width / aspect)
            
            # Read and resample data
            data = src.read(
                1,
                out_shape=(height, width),
                resampling=Resampling.bilinear,
                masked=True
            )
            
            # Create colormap visualization
            vmin = np.nanmin(data)
            vmax = np.nanmax(data)
            
            # Normalize data
            norm_data = (data - vmin) / (vmax - vmin)
            
            # Apply colormap
            cmap = cm.get_cmap(colormap)
            colored = cmap(norm_data)
            
            # Convert to RGBA image
            img = Image.fromarray((colored * 255).astype(np.uint8))
            
            # Save to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return Response(
                content=img_bytes.getvalue(),
                media_type="image/png",
                headers={
                    "Cache-Control": "max-age=3600"
                }
            )
    except Exception as e:
        raise HTTPException(500, f"Error generating preview: {str(e)}")


@router.get("/{hazard_id}/tiles/{z}/{x}/{y}")
async def get_hazard_tile(
    hazard_id: int,
    z: int,
    x: int,
    y: int,
    colormap: str = Query("Blues", description="Colormap name"),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve raster tiles for web mapping (TMS standard)."""
    hazard = await db.get(Hazard, hazard_id)
    if not hazard:
        raise HTTPException(404, "Hazard not found")
    
    try:
        with Reader(hazard.wse_raster_path) as src:
            img = src.tile(x, y, z)
            
            # Apply colormap to single band data
            stats = src.statistics()
            vmin = stats[1]['min']
            vmax = stats[1]['max']
            
            # Create a colormap
            cmap = cm.get_cmap(colormap)
            
            # Normalize and apply colormap
            data = img.data[0]
            mask = img.mask[0]
            
            norm_data = (data - vmin) / (vmax - vmin)
            colored = cmap(norm_data)
            
            # Apply mask
            colored[~mask] = [0, 0, 0, 0]
            
            # Convert to PIL Image
            img_array = (colored * 255).astype(np.uint8)
            pil_img = Image.fromarray(img_array)
            
            # Save to bytes
            img_bytes = io.BytesIO()
            pil_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            return Response(
                content=img_bytes.getvalue(),
                media_type="image/png",
                headers={
                    "Cache-Control": "max-age=86400",
                    "Access-Control-Allow-Origin": "*"
                }
            )
    except Exception as e:
        # Return transparent tile for out of bounds
        if "TileOutsideBounds" in str(e):
            transparent = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            img_bytes = io.BytesIO()
            transparent.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            return Response(
                content=img_bytes.getvalue(),
                media_type="image/png"
            )
        raise HTTPException(500, f"Error generating tile: {str(e)}")
