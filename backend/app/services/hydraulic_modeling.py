"""
Hydraulic modeling service for flood intervention analysis.

This module implements simplified flood modeling to demonstrate how 
interventions (levees, dams) affect water surface elevations.
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

logger = logging.getLogger(__name__)

class HydraulicModelingError(Exception):
    """Custom exception for hydraulic modeling errors."""
    pass

class SimplifiedFloodModeler:
    """
    Simplified flood modeling engine.
    
    This implements basic hydraulic concepts:
    - Levees: Create barriers that reduce water levels on protected side
    - Dams: Create backwater effects upstream, reduce flow downstream
    """
    
    def __init__(self, original_raster_path: str):
        """Initialize modeler with original WSE raster."""
        self.original_raster_path = original_raster_path
        self.raster_data = None
        self.transform = None
        self.crs = None
        self.nodata = None
        
        self._load_raster()
    
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
            raise HydraulicModelingError(f"Failed to load raster {self.original_raster_path}: {e}")
    
    def apply_intervention(
        self, 
        geometry: Dict[str, Any], 
        intervention_type: str, 
        parameters: Dict[str, float]
    ) -> np.ndarray:
        """
        Apply intervention to the WSE raster.
        
        Args:
            geometry: GeoJSON geometry of intervention
            intervention_type: 'levee' or 'dam'
            parameters: Intervention parameters (height, width, etc.)
            
        Returns:
            Modified WSE array
        """
        logger.info(f"Applying {intervention_type} intervention with parameters: {parameters}")
        
        # Create a copy of original data to modify
        modified_wse = self.raster_data.copy()
        
        if intervention_type == 'levee':
            modified_wse = self._apply_levee(modified_wse, geometry, parameters)
        elif intervention_type == 'dam':
            modified_wse = self._apply_dam(modified_wse, geometry, parameters)
        else:
            raise HydraulicModelingError(f"Unknown intervention type: {intervention_type}")
        
        return modified_wse
    
    def _apply_levee(
        self, 
        wse_array: np.ndarray, 
        geometry: Dict[str, Any], 
        parameters: Dict[str, float]
    ) -> np.ndarray:
        """
        Apply levee intervention.
        
        Levee logic:
        1. Create a barrier along the levee line
        2. Determine which side is "protected" (lower elevation side)
        3. Reduce water levels on protected side where they exceed levee height
        """
        height = parameters['height']
        top_width = parameters.get('top_width', 2.0)
        
        try:
            # Convert GeoJSON to Shapely geometry
            if geometry['type'] == 'LineString':
                line = LineString(geometry['coordinates'])
            else:
                raise HydraulicModelingError(f"Levee must be LineString, got {geometry['type']}")
            
            # Create levee buffer zone (protection zone extends from levee)
            buffer_distance = self._get_pixel_size() * 10  # 10 pixels wide protection zone
            protection_zone = line.buffer(buffer_distance)
            
            # Rasterize the protection zone
            protection_mask = self._rasterize_geometry(protection_zone)
            
            if not np.any(protection_mask):
                logger.warning("Levee protection zone is empty")
                return wse_array
            
            # Calculate levee crest elevation (ground + levee height)
            # For simplicity, assume ground elevation = current WSE minimum in area
            ground_elevation = np.nanmin(wse_array[protection_mask])
            levee_crest = ground_elevation + height
            
            logger.info(f"Levee: ground={ground_elevation:.2f}m, crest={levee_crest:.2f}m")
            
            # Apply levee protection: cap water levels at levee crest height
            modified_wse = wse_array.copy()
            protected_areas = protection_mask & (wse_array > levee_crest)
            
            if np.any(protected_areas):
                # Gradually reduce water levels behind levee
                reduction_factor = 0.7  # Reduce water by 30% in protected areas
                modified_wse[protected_areas] = (
                    levee_crest + (wse_array[protected_areas] - levee_crest) * reduction_factor
                )
                
                # Smooth the transition
                modified_wse = self._smooth_transition(modified_wse, protection_mask)
                
                logger.info(f"Applied levee protection to {np.sum(protected_areas)} pixels")
            
            return modified_wse
            
        except Exception as e:
            logger.error(f"Error applying levee: {e}")
            raise HydraulicModelingError(f"Failed to apply levee: {e}")
    
    def _apply_dam(
        self, 
        wse_array: np.ndarray, 
        geometry: Dict[str, Any], 
        parameters: Dict[str, float]
    ) -> np.ndarray:
        """
        Apply dam intervention.
        
        Dam logic:
        1. Create impoundment upstream (higher water levels)
        2. Reduce flow downstream (lower water levels)
        3. Consider spillway effects
        """
        height = parameters['height']
        width = parameters['width']
        crest_elevation = parameters.get('crest_elevation', None)
        
        try:
            # Convert geometry
            if geometry['type'] == 'LineString':
                dam_line = LineString(geometry['coordinates'])
            else:
                raise HydraulicModelingError(f"Dam must be LineString, got {geometry['type']}")
            
            # Create upstream and downstream zones
            buffer_distance = self._get_pixel_size() * 20  # Larger effect zone
            
            # Simple approach: determine flow direction from elevation gradient
            upstream_zone, downstream_zone = self._determine_flow_zones(dam_line, wse_array, buffer_distance)
            
            # Apply dam effects
            modified_wse = wse_array.copy()
            
            # Upstream: create reservoir (raise water levels)
            if np.any(upstream_zone):
                base_elevation = np.nanmean(wse_array[upstream_zone])
                if crest_elevation:
                    reservoir_level = min(crest_elevation, base_elevation + height * 0.8)
                else:
                    reservoir_level = base_elevation + height * 0.6
                
                # Gradually raise water levels upstream
                upstream_boost = np.minimum(
                    reservoir_level - wse_array[upstream_zone],
                    height * 0.5
                )
                upstream_boost = np.maximum(upstream_boost, 0)  # Only increase, don't decrease
                modified_wse[upstream_zone] += upstream_boost
                
                logger.info(f"Dam upstream: raised water to {reservoir_level:.2f}m")
            
            # Downstream: reduce water levels
            if np.any(downstream_zone):
                reduction = height * 0.3  # Reduce by 30% of dam height
                modified_wse[downstream_zone] = np.maximum(
                    modified_wse[downstream_zone] - reduction,
                    modified_wse[downstream_zone] * 0.7  # Don't reduce below 70% of original
                )
                
                logger.info(f"Dam downstream: reduced water by {reduction:.2f}m")
            
            # Smooth transitions
            all_zones = upstream_zone | downstream_zone
            modified_wse = self._smooth_transition(modified_wse, all_zones)
            
            return modified_wse
            
        except Exception as e:
            logger.error(f"Error applying dam: {e}")
            raise HydraulicModelingError(f"Failed to apply dam: {e}")
    
    def _determine_flow_zones(
        self, 
        dam_line: LineString, 
        wse_array: np.ndarray, 
        buffer_distance: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Determine upstream and downstream zones based on elevation gradient."""
        
        # Create buffer around dam
        dam_buffer = dam_line.buffer(buffer_distance)
        dam_mask = self._rasterize_geometry(dam_buffer)
        
        if not np.any(dam_mask):
            return np.zeros_like(wse_array, dtype=bool), np.zeros_like(wse_array, dtype=bool)
        
        # Get dam center point
        dam_center = dam_line.centroid
        center_row, center_col = self._geometry_to_pixel(dam_center)
        
        # Create distance-based zones (simplified)
        rows, cols = np.ogrid[:wse_array.shape[0], :wse_array.shape[1]]
        
        # Calculate distance from dam center
        distances = np.sqrt((rows - center_row)**2 + (cols - center_col)**2)
        
        # Create zones within reasonable distance
        max_distance = buffer_distance / self._get_pixel_size()
        nearby = distances < max_distance
        
        # Simple heuristic: upstream = higher elevation side, downstream = lower elevation side
        dam_elevation = np.nanmean(wse_array[dam_mask])
        
        upstream_zone = nearby & (wse_array > dam_elevation)
        downstream_zone = nearby & (wse_array < dam_elevation)
        
        return upstream_zone, downstream_zone
    
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
    
    def _geometry_to_pixel(self, geometry) -> Tuple[int, int]:
        """Convert geometry point to pixel coordinates."""
        x, y = geometry.x, geometry.y
        row, col = rasterio.transform.rowcol(self.transform, x, y)
        return int(row), int(col)
    
    def _get_pixel_size(self) -> float:
        """Get pixel size in map units."""
        return abs(self.transform.a)  # Assuming square pixels
    
    def _smooth_transition(self, array: np.ndarray, affected_mask: np.ndarray) -> np.ndarray:
        """Apply Gaussian smoothing to transition zones."""
        try:
            # Create a slightly larger mask for smoothing
            kernel = np.ones((3, 3))
            expanded_mask = ndimage.binary_dilation(affected_mask, kernel)
            
            # Apply light Gaussian smoothing only to transition areas
            smoothed = ndimage.gaussian_filter(array, sigma=1.0)
            
            # Blend original and smoothed in transition zones
            result = array.copy()
            transition_zone = expanded_mask & ~affected_mask
            if np.any(transition_zone):
                result[transition_zone] = (
                    0.7 * array[transition_zone] + 
                    0.3 * smoothed[transition_zone]
                )
            
            return result
            
        except Exception as e:
            logger.warning(f"Error in smoothing: {e}")
            return array
    
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
            raise HydraulicModelingError(f"Failed to save raster to {output_path}: {e}")


def process_intervention_modeling(
    intervention_id: int,
    original_raster_path: str,
    intervention_geometry: Dict[str, Any],
    intervention_type: str,
    intervention_parameters: Dict[str, float],
    output_raster_path: str
) -> Dict[str, Any]:
    """
    Main function to process intervention hydraulic modeling.
    
    Args:
        intervention_id: ID of the intervention
        original_raster_path: Path to original WSE raster
        intervention_geometry: GeoJSON geometry
        intervention_type: 'levee' or 'dam'
        intervention_parameters: Parameters dict
        output_raster_path: Output path for modified raster
        
    Returns:
        Dictionary with modeling results and statistics
    """
    try:
        logger.info(f"Starting hydraulic modeling for intervention {intervention_id}")
        
        # Use improved modeling for levees
        if intervention_type == 'levee':
            try:
                from app.services.improved_hydraulic_modeling import process_improved_levee_modeling
                return process_improved_levee_modeling(
                    intervention_id,
                    original_raster_path,
                    intervention_geometry,
                    intervention_parameters,
                    output_raster_path
                )
            except ImportError:
                logger.warning("Improved modeling not available, falling back to simplified model")
        
        # Initialize modeler
        modeler = SimplifiedFloodModeler(original_raster_path)
        
        # Apply intervention
        modified_wse = modeler.apply_intervention(
            intervention_geometry,
            intervention_type,
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
            'intervention_type': intervention_type,
            'output_raster_path': output_raster_path,
            'original_stats': original_stats,
            'modified_stats': modified_stats,
            'reduction_stats': reduction_stats,
            'model_type': 'simplified_flood_model_v1'
        }
        
        logger.info(f"Modeling completed successfully. Affected {reduction_stats['affected_area_pixels']} pixels")
        return results
        
    except Exception as e:
        logger.error(f"Hydraulic modeling failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'intervention_id': intervention_id
        }