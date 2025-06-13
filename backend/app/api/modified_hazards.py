"""
API endpoints for modified hazards visualization.
"""

import logging
import io
from pathlib import Path
from typing import Dict, Any

import rasterio
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from fastapi import APIRouter, HTTPException, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from rio_tiler.io import Reader
from rio_tiler.models import ImageData
from rio_tiler.colormap import cmap

from app.db import get_async_session
from app.models import ModifiedHazard

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modified-hazards", tags=["Modified Hazards"])

@router.get("/{modified_hazard_id}/info")
async def get_modified_hazard_info(
    modified_hazard_id: int,
    db: AsyncSession = Depends(get_async_session)
) -> Dict[str, Any]:
    """Get modified hazard metadata and statistics."""
    
    modified_hazard = await db.get(ModifiedHazard, modified_hazard_id)
    if not modified_hazard:
        raise HTTPException(404, "Modified hazard not found")
    
    try:
        with rasterio.open(modified_hazard.wse_raster_path) as src:
            # Get basic metadata
            bounds = src.bounds
            width = src.width
            height = src.height
            crs = str(src.crs)
            
            # Calculate statistics
            data = src.read(1, masked=True)
            stats = {
                "min": float(np.nanmin(data)),
                "max": float(np.nanmax(data)),
                "mean": float(np.nanmean(data)),
                "std": float(np.nanstd(data))
            }
            
        return {
            "id": modified_hazard.id,
            "name": modified_hazard.name,
            "intervention_id": modified_hazard.intervention_id,
            "model_type": modified_hazard.model_type,
            "bounds": {
                "minx": bounds.left,
                "miny": bounds.bottom,
                "maxx": bounds.right,
                "maxy": bounds.top
            },
            "width": width,
            "height": height,
            "crs": crs,
            "statistics": stats,
            "model_results": modified_hazard.model_results
        }
        
    except Exception as e:
        logger.error(f"Error reading modified hazard raster: {e}")
        raise HTTPException(500, f"Error reading modified hazard data: {str(e)}")


@router.get("/{modified_hazard_id}/preview")
async def get_modified_hazard_preview(
    modified_hazard_id: int,
    width: int = 800,
    height: int = 600,
    colormap: str = "Blues",
    db: AsyncSession = Depends(get_async_session)
):
    """Generate a preview image of the modified hazard."""
    
    modified_hazard = await db.get(ModifiedHazard, modified_hazard_id)
    if not modified_hazard:
        raise HTTPException(404, "Modified hazard not found")
    
    try:
        with rasterio.open(modified_hazard.wse_raster_path) as src:
            # Read the data
            data = src.read(1, masked=True)
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width/100, height/100), dpi=100)
            
            # Plot with specified colormap
            cm = plt.get_cmap(colormap)
            im = ax.imshow(data, cmap=cm, aspect='equal')
            
            # Add colorbar
            plt.colorbar(im, ax=ax, label='Water Surface Elevation (m)')
            ax.set_title(f'{modified_hazard.name}')
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            
            # Save to bytes
            img_bytes = io.BytesIO()
            plt.savefig(img_bytes, format='PNG', bbox_inches='tight', dpi=100)
            plt.close()
            img_bytes.seek(0)
            
            return Response(
                content=img_bytes.getvalue(),
                media_type="image/png",
                headers={
                    "Cache-Control": "max-age=3600",
                    "Access-Control-Allow-Origin": "*"
                }
            )
            
    except Exception as e:
        logger.error(f"Error generating modified hazard preview: {e}")
        raise HTTPException(500, f"Error generating preview: {str(e)}")


@router.get("/{modified_hazard_id}/tiles/{z}/{x}/{y}")
async def get_modified_hazard_tile(
    modified_hazard_id: int,
    z: int,
    x: int,
    y: int,
    colormap: str = "Blues",
    db: AsyncSession = Depends(get_async_session)
):
    """Get a map tile for the modified hazard."""
    
    modified_hazard = await db.get(ModifiedHazard, modified_hazard_id)
    if not modified_hazard:
        raise HTTPException(404, "Modified hazard not found")
    
    try:
        with Reader(modified_hazard.wse_raster_path) as cog:
            # Get the tile
            tile = cog.tile(x, y, z)
            
            # Get global statistics for consistent normalization (like original hazard)
            stats = cog.statistics()
            # rio-tiler returns stats as {band_name: {min, max, ...}}
            band_stats = stats.get('1') or stats.get('b1') or list(stats.values())[0]
            vmin = band_stats.min
            vmax = band_stats.max
            
            # Get matplotlib colormap
            try:
                cm = plt.get_cmap(colormap)
            except ValueError:
                cm = plt.get_cmap("Blues")  # fallback
            
            # Process tile data
            img_data = tile.data[0]
            mask_data = tile.mask
            
            # Normalize using global min/max (consistent across all tiles)
            if vmax > vmin:
                normalized = (img_data - vmin) / (vmax - vmin)
                normalized = np.clip(normalized, 0, 1)
            else:
                normalized = np.zeros_like(img_data, dtype=np.float32)
            
            # Apply colormap
            colored = cm(normalized)
            
            # Apply mask (set to transparent)
            if mask_data is not None:
                colored[~mask_data] = [0, 0, 0, 0]  # Transparent for masked areas
            
            # Convert to PIL Image
            pil_img = Image.fromarray((colored * 255).astype(np.uint8), 'RGBA')
            
            # Return as PNG
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
        logger.error(f"Error generating modified hazard tile: {str(e)}", exc_info=True)
        # Return transparent tile for errors
        transparent = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        img_bytes = io.BytesIO()
        transparent.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        return Response(
            content=img_bytes.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "max-age=86400",
                "Access-Control-Allow-Origin": "*"
            }
        )