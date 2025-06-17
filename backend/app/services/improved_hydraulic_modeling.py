"""
Improved hydraulic modeling with proper water blocking for levees.

This implementation uses a flood-fill algorithm that respects levee barriers,
creating realistic water blocking effects.
"""

import logging
import numpy as np
import rasterio
from rasterio.transform import xy
from rasterio.features import rasterize
from pathlib import Path
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import transform
from shapely.affinity import scale
from scipy import ndimage
import geopandas as gpd
from typing import Dict, Any, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)


class ImprovedFloodModeler:
    """
    Improved flood modeling with proper barrier physics.
    """
    
    def __init__(self, original_raster_path: str):
        """Initialize modeler with original WSE raster."""
        self.original_raster_path = original_raster_path
        self.raster_data = None
        self.transform = None
        self.crs = None
        self.nodata = None
        self.terrain = None  # Will estimate terrain from WSE
        
        self._load_raster()
        self._estimate_terrain()
    
    def _load_raster(self):
        """Load the original WSE raster data."""
        try:
            with rasterio.open(self.original_raster_path) as src:
                self.raster_data = src.read(1, masked=True)
                self.transform = src.transform
                self.crs = src.crs
                self.nodata = src.nodata
                self.bounds = src.bounds
                
            logger.info(f"Loaded raster: {self.raster_data.shape}, bounds: {self.bounds}")
            
        except Exception as e:
            raise Exception(f"Failed to load raster {self.original_raster_path}: {e}")
    
    def _estimate_terrain(self):
        """Estimate ground terrain from water surface elevation."""
        # Simple approach: assume terrain is some percentage below WSE
        # In reality, you'd want a separate DEM
        self.terrain = self.raster_data * 0.85  # Assume terrain is 85% of WSE
        logger.info("Estimated terrain from WSE")
    
    def apply_levee_intervention(
        self, 
        geometry: Dict[str, Any], 
        parameters: Dict[str, float]
    ) -> np.ndarray:
        """
        Apply levee intervention with proper water blocking.
        
        This creates an actual barrier that water cannot cross.
        """
        height = parameters['height']
        
        try:
            # Convert GeoJSON to Shapely geometry
            if geometry['type'] == 'LineString':
                levee_line = LineString(geometry['coordinates'])
            else:
                raise Exception(f"Levee must be LineString, got {geometry['type']}")
            
            # Create levee barrier mask
            barrier_mask = self._create_levee_barrier(levee_line, height)
            
            # Apply flood routing with barrier
            modified_wse = self._route_water_with_barrier(
                self.raster_data.copy(), 
                barrier_mask, 
                height
            )
            
            return modified_wse
            
        except Exception as e:
            logger.error(f"Error applying levee: {e}")
            raise Exception(f"Failed to apply levee: {e}")
    
    def _create_levee_barrier(self, levee_line: LineString, height: float) -> np.ndarray:
        """Create a barrier mask from the levee line."""
        
        # Buffer the line slightly to create a barrier zone
        pixel_size = self._get_pixel_size()
        buffer_distance = pixel_size * 0.5  # Half pixel buffer
        
        barrier_geom = levee_line.buffer(buffer_distance)
        barrier_mask = self._rasterize_geometry(barrier_geom)
        
        logger.info(f"Created barrier with {np.sum(barrier_mask)} pixels")
        return barrier_mask
    
    def _route_water_with_barrier(
        self, 
        wse_array: np.ndarray, 
        barrier_mask: np.ndarray, 
        levee_height: float
    ) -> np.ndarray:
        """
        Route water around barriers using flood-fill algorithm.
        
        This simulates water finding its way around obstacles.
        """
        
        # Create levee elevation - levee blocks water above this height
        ground_elevation = np.nanmin(self.terrain[barrier_mask]) if np.any(barrier_mask) else np.nanmin(self.terrain)
        levee_crest_elevation = ground_elevation + levee_height
        
        logger.info(f"Levee crest elevation: {levee_crest_elevation:.2f}m")
        
        # Find water source areas (highest water elevations)
        water_sources = wse_array > np.percentile(wse_array[~np.isnan(wse_array)], 90)
        
        # Create modified WSE array
        modified_wse = self.terrain.copy()  # Start with ground level
        
        # Use flood-fill algorithm respecting barriers
        visited = np.zeros_like(wse_array, dtype=bool)
        
        # Start flood-fill from water source areas
        queue = deque()
        
        # Add all high-water source pixels to queue
        for y, x in np.argwhere(water_sources):
            if not visited[y, x]:
                queue.append((y, x, wse_array[y, x]))
                visited[y, x] = True
                modified_wse[y, x] = wse_array[y, x]
        
        # Flood-fill with barrier respect
        while queue:
            y, x, water_level = queue.popleft()
            
            # Check 4-connected neighbors
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                
                # Check bounds
                if not (0 <= ny < wse_array.shape[0] and 0 <= nx < wse_array.shape[1]):
                    continue
                
                # Skip if already visited
                if visited[ny, nx]:
                    continue
                
                # Check if barrier blocks this flow
                if barrier_mask[ny, nx] and water_level > levee_crest_elevation:
                    # Water is blocked by levee
                    continue
                
                # Check if water can flow to this cell
                neighbor_terrain = self.terrain[ny, nx]
                
                # Water flows if it's above the terrain level
                if water_level > neighbor_terrain:
                    # Calculate water level accounting for flow and spreading
                    flow_loss = 0.01  # Small loss per cell (friction)
                    new_water_level = max(
                        water_level - flow_loss,
                        neighbor_terrain,
                        modified_wse[ny, nx]
                    )
                    
                    # Only update if this gives a higher water level
                    if new_water_level > modified_wse[ny, nx]:
                        modified_wse[ny, nx] = new_water_level
                        queue.append((ny, nx, new_water_level))
                        visited[ny, nx] = True
        
        # Smooth the results slightly to remove artifacts
        modified_wse = ndimage.gaussian_filter(modified_wse, sigma=0.5)
        
        # Ensure water doesn't go below terrain
        modified_wse = np.maximum(modified_wse, self.terrain)
        
        # Calculate effectiveness
        original_flooded = np.sum(wse_array > self.terrain + 0.1)
        modified_flooded = np.sum(modified_wse > self.terrain + 0.1)
        reduction_pct = (original_flooded - modified_flooded) / original_flooded * 100
        
        logger.info(f"Flood reduction: {reduction_pct:.1f}% ({original_flooded} -> {modified_flooded} flooded pixels)")
        
        return modified_wse
    
    def _rasterize_geometry(self, geometry) -> np.ndarray:
        """Convert Shapely geometry to raster mask."""
        try:
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame([1], geometry=[geometry], crs=self.crs)
            
            # Rasterize
            mask = rasterize(
                [(geom, 1) for geom in gdf.geometry],
                out_shape=self.raster_data.shape,
                transform=self.transform,
                fill=0,
                dtype=np.uint8
            )
            
            return mask.astype(bool)
            
        except Exception as e:
            logger.error(f"Error rasterizing geometry: {e}")
            return np.zeros_like(self.raster_data, dtype=bool)
    
    def _get_pixel_size(self) -> float:
        """Get pixel size in map units."""
        return abs(self.transform.a)  # Assuming square pixels
    
    def save_modified_raster(self, modified_wse: np.ndarray, output_path: str):
        """Save the modified WSE array to a new raster file."""
        try:
            # Copy metadata from original
            with rasterio.open(self.original_raster_path) as src:
                profile = src.profile.copy()
            
            # Update profile for output
            profile.update({
                'dtype': 'float32',
                'compress': 'lzw'
            })
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Write the modified raster
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(modified_wse.astype(np.float32), 1)
            
            logger.info(f"Saved modified raster to {output_path}")
            
        except Exception as e:
            raise Exception(f"Failed to save raster to {output_path}: {e}")


def process_improved_levee_modeling(
    intervention_id: int,
    original_raster_path: str,
    intervention_geometry: Dict[str, Any],
    intervention_parameters: Dict[str, float],
    output_raster_path: str
) -> Dict[str, Any]:
    """
    Process levee intervention with improved modeling.
    """
    try:
        logger.info(f"Starting improved levee modeling for intervention {intervention_id}")
        
        # Initialize improved modeler
        modeler = ImprovedFloodModeler(original_raster_path)
        
        # Apply levee intervention
        modified_wse = modeler.apply_levee_intervention(
            intervention_geometry,
            intervention_parameters
        )
        
        # Save modified raster
        modeler.save_modified_raster(modified_wse, output_raster_path)
        
        # Calculate statistics
        original_stats = {
            'min': float(np.nanmin(modeler.raster_data)),
            'max': float(np.nanmax(modeler.raster_data)),
            'mean': float(np.nanmean(modeler.raster_data))
        }
        
        modified_stats = {
            'min': float(np.nanmin(modified_wse)),
            'max': float(np.nanmax(modified_wse)),
            'mean': float(np.nanmean(modified_wse))
        }
        
        # Calculate reduction statistics
        valid_mask = ~np.isnan(modeler.raster_data) & ~np.isnan(modified_wse)
        water_reduction = modeler.raster_data[valid_mask] - modified_wse[valid_mask]
        
        reduction_stats = {
            'total_reduction_m3': float(np.sum(water_reduction[water_reduction > 0])),
            'max_reduction_m': float(np.max(water_reduction)),
            'mean_reduction_m': float(np.mean(water_reduction[water_reduction > 0])) if np.any(water_reduction > 0) else 0.0,
            'affected_area_pixels': int(np.sum(np.abs(water_reduction) > 0.01))  # More than 1cm change
        }
        
        results = {
            'success': True,
            'intervention_id': intervention_id,
            'intervention_type': 'levee',
            'output_raster_path': output_raster_path,
            'original_stats': original_stats,
            'modified_stats': modified_stats,
            'reduction_stats': reduction_stats,
            'model_type': 'improved_flood_model_v2'
        }
        
        logger.info(f"Improved modeling completed. Affected {reduction_stats['affected_area_pixels']} pixels")
        return results
        
    except Exception as e:
        logger.error(f"Improved hydraulic modeling failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'intervention_id': intervention_id
        }