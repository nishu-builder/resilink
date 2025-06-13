#!/usr/bin/env python3
"""
Create a more realistic riverine flood hazard TIF file for Denver.
This script generates a water surface elevation raster that models
flooding along river channels with realistic flood patterns.

Run this inside the backend Docker container:
    task enter
    python scripts/create_realistic_flood_hazard.py
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from scipy.ndimage import gaussian_filter, distance_transform_edt


def create_river_mask(width, height, num_rivers=2):
    """Create a mask with river channels"""
    river_mask = np.zeros((height, width), dtype=bool)
    
    # Main river (South Platte River approximate path)
    # Creates a meandering path from southwest to northeast
    for i in range(width):
        # River meanders with sine wave
        base_y = int(height * 0.7 - (i / width) * height * 0.4)
        meander = int(10 * np.sin(i * 0.05))
        y = base_y + meander
        
        # River width varies
        river_width = 3 + int(2 * np.sin(i * 0.02))
        
        for dy in range(-river_width, river_width + 1):
            if 0 <= y + dy < height:
                river_mask[y + dy, i] = True
    
    # Tributary (Cherry Creek approximate path)
    # Joins main river from southeast
    if num_rivers > 1:
        for i in range(int(width * 0.6)):
            base_y = int(height * 0.9 - (i / (width * 0.6)) * height * 0.2)
            meander = int(5 * np.sin(i * 0.08 + 2))
            y = base_y + meander
            
            river_width = 2 + int(np.sin(i * 0.03))
            
            for dy in range(-river_width, river_width + 1):
                if 0 <= y + dy < height:
                    river_mask[y + dy, i] = True
    
    return river_mask


def create_terrain_elevation(width, height, base_elevation=1600):
    """Create realistic terrain elevation with valley around rivers"""
    # Create base terrain with gentle slope from west to east
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    
    # Base elevation decreases from west to east
    terrain = base_elevation + 20 * (1 - X) + 5 * (1 - Y)
    
    # Add some hills and variation
    terrain += 3 * np.sin(X * 10) * np.cos(Y * 8)
    terrain += 2 * np.sin(X * 15 + 1) * np.cos(Y * 12 + 2)
    
    # Smooth the terrain
    terrain = gaussian_filter(terrain, sigma=2)
    
    return terrain


def create_flood_surface(river_mask, terrain, flood_stage=2.0, flood_extent=30):
    """Create water surface elevation based on river flooding"""
    # Get distance from river channels
    distance_from_river = distance_transform_edt(~river_mask)
    
    # Create flood mask based on distance and terrain
    # Flood extends further in flatter areas
    terrain_gradient = np.gradient(terrain)[0]**2 + np.gradient(terrain)[1]**2
    terrain_gradient = np.sqrt(terrain_gradient)
    
    # Adaptive flood extent based on terrain slope
    local_flood_extent = flood_extent * (1 + np.exp(-terrain_gradient * 10))
    flood_influence = np.exp(-distance_from_river / local_flood_extent)
    
    # Water surface follows terrain but is elevated near rivers
    water_surface = terrain.copy()
    
    # In river channels, water is at flood stage above terrain
    water_surface[river_mask] = terrain[river_mask] + flood_stage
    
    # Flood water spreads from rivers with decreasing elevation
    flood_elevation = terrain + flood_stage * flood_influence
    
    # Water finds its level - smooth the flood surface
    flood_elevation = gaussian_filter(flood_elevation, sigma=3)
    
    # Only show water where it would actually flood (above terrain)
    water_surface = np.maximum(terrain, flood_elevation)
    
    # Add some realistic variation to water surface
    noise = np.random.normal(0, 0.05, water_surface.shape)
    water_surface += gaussian_filter(noise, sigma=1)
    
    return water_surface


def main():
    # Parameters
    width, height = 100, 100
    west, south, east, north = -105.0, 39.7, -104.9, 39.8  # Denver area
    
    # Create river channels
    print("Creating river channels...")
    river_mask = create_river_mask(width, height, num_rivers=2)
    
    # Create terrain elevation
    print("Creating terrain elevation...")
    terrain = create_terrain_elevation(width, height, base_elevation=1600)
    
    # Create flood scenarios
    scenarios = {
        '10yr_flood': 1.5,  # 10-year flood: 1.5m flood stage
        '50yr_flood': 2.5,  # 50-year flood: 2.5m flood stage
        '100yr_flood': 3.5, # 100-year flood: 3.5m flood stage
        '500yr_flood': 5.0  # 500-year flood: 5.0m flood stage
    }
    
    for scenario_name, flood_stage in scenarios.items():
        print(f"Creating {scenario_name} with {flood_stage}m flood stage...")
        
        # Create water surface elevation
        wse = create_flood_surface(river_mask, terrain, 
                                  flood_stage=flood_stage, 
                                  flood_extent=20 + flood_stage * 5)
        
        # Create transform
        transform = from_bounds(west, south, east, north, width, height)
        
        # Write the raster to the data directory in the container
        output_path = f'/app/data/denver_riverine_{scenario_name}.tif'
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype='float32',
            crs='EPSG:4326',
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(wse.astype('float32'), 1)
            dst.update_tags(AREA_OR_POINT='Area')
        
        print(f"Created: {output_path}")
        print(f"  WSE range: {wse.min():.1f} - {wse.max():.1f} meters")
        print(f"  Flood depth range: 0 - {(wse - terrain).max():.1f} meters")
        print()


if __name__ == '__main__':
    main()