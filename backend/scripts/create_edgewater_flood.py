#!/usr/bin/env python3
"""
Create a realistic flood hazard TIF file for Denver focused on Sloan's Lake in Edgewater.
This script models flooding from the lake overflowing and flowing downstream.
"""

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from scipy.ndimage import gaussian_filter, distance_transform_edt
import math


def create_lake_and_outflow(width, height):
    """Create Sloan's Lake and its outflow channels"""
    lake_mask = np.zeros((height, width), dtype=bool)
    outflow_mask = np.zeros((height, width), dtype=bool)
    
    # Sloan's Lake is roughly at coordinates -105.055, 39.745
    # In our grid (west=-105.0, east=-104.9, south=39.7, north=39.8)
    # Lake center is at approximately x=45, y=45 in a 100x100 grid
    
    lake_center_x = 45  # Longitude position
    lake_center_y = 45  # Latitude position
    
    # Create oval-shaped lake (Sloan's Lake is roughly oval)
    for y in range(height):
        for x in range(width):
            # Distance from lake center
            dx = (x - lake_center_x) / 8.0  # Lake is wider east-west
            dy = (y - lake_center_y) / 6.0  # Lake is narrower north-south
            distance = dx**2 + dy**2
            
            if distance <= 1.0:
                lake_mask[y, x] = True
    
    # Create outflow channels from the lake
    # Main outflow goes east and slightly south (towards South Platte)
    for i in range(width - lake_center_x):
        x = lake_center_x + i
        if x >= width:
            break
            
        # Channel meanders slightly south as it flows east
        base_y = lake_center_y + int(i * 0.2)  # Gentle southward slope
        meander = int(2 * np.sin(i * 0.1))  # Small meanders
        y = base_y + meander
        
        if 0 <= y < height:
            # Channel width decreases with distance
            channel_width = max(1, 3 - i // 15)
            for dy in range(-channel_width, channel_width + 1):
                if 0 <= y + dy < height:
                    outflow_mask[y + dy, x] = True
    
    # Secondary outflow goes southeast
    for i in range(min(width - lake_center_x, height - lake_center_y) // 2):
        x = lake_center_x + i
        y = lake_center_y + int(i * 0.8)  # Steeper southward slope
        
        if x < width and y < height:
            channel_width = max(1, 2 - i // 10)
            for dy in range(-channel_width, channel_width + 1):
                for dx in range(-channel_width, channel_width + 1):
                    if (0 <= y + dy < height and 0 <= x + dx < width):
                        outflow_mask[y + dy, x + dx] = True
    
    return lake_mask, outflow_mask


def create_denver_terrain(width, height, base_elevation=1640):
    """Create realistic terrain for Denver area with Sloan's Lake depression"""
    # Denver coordinates: west=-105.0, east=-104.9, south=39.7, north=39.8
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    X, Y = np.meshgrid(x, y)
    
    # Base elevation: generally slopes down from west to east
    # Denver is at about 1640m elevation near Sloan's Lake
    terrain = base_elevation + 15 * (1 - X)  # Slopes down to the east
    
    # North-south gradient (slight slope down to the south)
    terrain += 5 * (1 - Y)
    
    # Create depression around Sloan's Lake
    lake_center_x = 45 / width  # Normalized coordinates
    lake_center_y = 45 / height
    
    # Lake depression
    lake_dist = np.sqrt((X - lake_center_x)**2 + (Y - lake_center_y)**2)
    lake_depression = 3 * np.exp(-lake_dist * 50)  # 3m deep depression
    terrain -= lake_depression
    
    # Add some realistic topographic variation
    terrain += 2 * np.sin(X * 12) * np.cos(Y * 8)
    terrain += 1.5 * np.sin(X * 20 + 1) * np.cos(Y * 15 + 2)
    
    # Smooth the terrain
    terrain = gaussian_filter(terrain, sigma=1.5)
    
    return terrain


def create_flood_from_lake(lake_mask, outflow_mask, terrain, flood_stage=2.0):
    """Create flooding that starts from the lake and flows through channels"""
    # Start with terrain elevation
    water_surface = terrain.copy()
    
    # Lake water level is at flood stage above normal
    # Assume normal lake level is 1m above lake bottom
    normal_lake_level = terrain[lake_mask].max() + 1.0
    flood_lake_level = normal_lake_level + flood_stage
    
    # Set lake water surface to flood level
    water_surface[lake_mask] = flood_lake_level
    
    # Water flows through outflow channels
    channel_mask = lake_mask | outflow_mask
    
    # Create distance from water sources (lake + channels)
    distance_from_water = distance_transform_edt(~channel_mask)
    
    # Flood influence decreases with distance and terrain slope
    terrain_gradient = np.gradient(terrain)[0]**2 + np.gradient(terrain)[1]**2
    terrain_gradient = np.sqrt(terrain_gradient)
    
    # Flood extent is based on terrain slope and distance
    # Flatter areas flood more extensively
    flood_extent = 25 * (1 + np.exp(-terrain_gradient * 5))
    flood_influence = np.exp(-distance_from_water / flood_extent)
    
    # Calculate flood water elevation
    # Water spreads from lake/channels and follows terrain
    flood_elevation = terrain + (flood_stage * 0.7) * flood_influence
    
    # In channels, water maintains higher elevation
    water_surface[outflow_mask] = np.maximum(
        water_surface[outflow_mask],
        terrain[outflow_mask] + flood_stage * 0.8
    )
    
    # Smooth the water surface to make it more realistic
    water_surface = gaussian_filter(water_surface, sigma=2)
    
    # Water can only exist above terrain
    water_surface = np.maximum(terrain, water_surface)
    
    # Add some realistic water surface variation
    noise = np.random.normal(0, 0.03, water_surface.shape)
    water_surface += gaussian_filter(noise, sigma=0.5)
    
    # Ensure lake maintains flood level
    water_surface[lake_mask] = flood_lake_level
    
    return water_surface


def main():
    # Parameters for Denver area
    width, height = 100, 100
    west, south, east, north = -105.0, 39.7, -104.9, 39.8  # Denver area
    
    print("Creating Sloan's Lake and outflow channels...")
    lake_mask, outflow_mask = create_lake_and_outflow(width, height)
    
    print("Creating Denver terrain with lake depression...")
    terrain = create_denver_terrain(width, height, base_elevation=1640)
    
    # Create different flood scenarios
    scenarios = {
        'lake_overflow_minor': 1.0,   # Minor lake overflow
        'lake_overflow_major': 2.5,   # Major lake overflow
        'lake_overflow_extreme': 4.0, # Extreme lake overflow
    }
    
    for scenario_name, flood_stage in scenarios.items():
        print(f"Creating {scenario_name} with {flood_stage}m flood stage...")
        
        # Create water surface elevation
        wse = create_flood_from_lake(lake_mask, outflow_mask, terrain, flood_stage)
        
        # Create transform
        transform = from_bounds(west, south, east, north, width, height)
        
        # Write the raster
        output_path = f'/app/data/denver_edgewater_{scenario_name}.tif'
        
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
        print(f"  Lake flood level: {wse[lake_mask].max():.1f} meters")
        print()


if __name__ == '__main__':
    main()