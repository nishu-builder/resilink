#!/usr/bin/env python3
"""
Generate a realistic building dataset for Denver with 50 buildings.

This script creates a shapefile with buildings distributed in interesting urban patterns:
1. Downtown cluster with higher density (40% of buildings)
2. Residential neighborhoods with medium density (20%)
3. Industrial/commercial areas along major corridors (20%)
4. Scattered buildings in suburban areas (20%)

The generated shapefile includes realistic attributes compatible with the 
flood risk analysis platform's building dataset upload endpoint.

Usage:
    Run this script in the backend Docker container:
    docker compose exec backend python /app/scripts/generate_denver_buildings.py
    
    Or copy this script to the backend scripts directory and run it.
    
Output:
    Creates Denver_Realistic_Buildings.zip in the current directory
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
import random
import os
import zipfile
from datetime import datetime

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)

# Denver coordinates
DENVER_CENTER = (-104.9903, 39.7392)

# Define cluster centers and characteristics
CLUSTERS = {
    'downtown': {
        'center': (-104.9903, 39.7392),
        'radius': 0.015,  # ~1 mile
        'density': 0.4,  # 40% of buildings
        'building_types': [
            ('COM1', 'S1', 0.3),  # Office buildings - steel frame
            ('COM2', 'C2', 0.2),  # Retail - concrete
            ('RES2', 'S2', 0.3),  # Multi-family residential - steel
            ('COM1', 'C1', 0.2),  # Office - concrete
        ],
        'stories_range': (5, 20),
        'year_range': (1960, 2024),
        'area_range': (5000, 15000)
    },
    'residential_north': {
        'center': (-104.9703, 39.7692),
        'radius': 0.020,
        'density': 0.2,
        'building_types': [
            ('RES1', 'W1', 0.5),  # Single family - wood
            ('RES2', 'W1', 0.3),  # Multi-family - wood
            ('RES1', 'W2', 0.2),  # Single family - wood
        ],
        'stories_range': (1, 3),
        'year_range': (1940, 2020),
        'area_range': (1200, 3500)
    },
    'industrial_corridor': {
        'center': (-105.0203, 39.7392),
        'radius': 0.025,
        'density': 0.2,
        'building_types': [
            ('IND1', 'S3', 0.4),  # Light industrial - steel
            ('COM2', 'S3', 0.3),  # Warehouse/retail - steel
            ('IND2', 'C3', 0.3),  # Heavy industrial - concrete
        ],
        'stories_range': (1, 3),
        'year_range': (1950, 2010),
        'area_range': (8000, 25000)
    },
    'suburban_scatter': {
        'center': (-104.9403, 39.7092),
        'radius': 0.035,
        'density': 0.2,
        'building_types': [
            ('RES1', 'W1', 0.6),  # Single family homes
            ('COM2', 'W1', 0.2),  # Strip malls
            ('RES2', 'W2', 0.2),  # Townhomes
        ],
        'stories_range': (1, 2),
        'year_range': (1970, 2024),
        'area_range': (1500, 4000)
    }
}

def generate_cluster_points(center, radius, n_points):
    """Generate random points within a circular cluster."""
    points = []
    while len(points) < n_points:
        # Generate random angle and distance
        angle = random.uniform(0, 2 * np.pi)
        # Use sqrt for uniform distribution within circle
        r = radius * np.sqrt(random.uniform(0, 1))
        
        # Calculate coordinates
        lon = center[0] + r * np.cos(angle)
        lat = center[1] + r * np.sin(angle)
        
        points.append((lon, lat))
    
    return points

def generate_buildings():
    """Generate the building dataset."""
    buildings = []
    building_id = 0
    
    # Generate buildings for each cluster
    for cluster_name, cluster_info in CLUSTERS.items():
        n_buildings = int(50 * cluster_info['density'])
        points = generate_cluster_points(
            cluster_info['center'], 
            cluster_info['radius'], 
            n_buildings
        )
        
        for lon, lat in points:
            # Select building type based on probabilities
            building_types = cluster_info['building_types']
            probs = [bt[2] for bt in building_types]
            selected = random.choices(building_types, weights=probs)[0]
            
            occtype, strtype = selected[0], selected[1]
            
            # Generate building attributes
            stories = random.randint(*cluster_info['stories_range'])
            yearbuilt = random.randint(*cluster_info['year_range'])
            
            # Building area depends on type and stories
            base_area = random.randint(*cluster_info['area_range'])
            if occtype == 'RES1':
                # Single family homes are smaller
                bldgarea = int(base_area * 0.6)
            elif stories > 5:
                # High-rise buildings have smaller footprints
                bldgarea = int(base_area * 0.4)
            else:
                bldgarea = base_area
            
            # Flood-related attributes
            # Higher flood risk near South Platte River (runs through downtown)
            dist_from_river = abs(lat - 39.7392) + abs(lon + 104.9903)
            if dist_from_river < 0.02:
                arch_flood = random.randint(1, 5)  # Higher flood risk
            else:
                arch_flood = random.randint(5, 15)  # Lower flood risk
            
            # First floor elevation (Denver is ~5280 ft)
            # Add some variation based on location
            base_elev = 5280.0
            elev_variation = random.uniform(-2, 5)
            ffe_elev = round(base_elev + elev_variation, 2)
            
            building = {
                'guid': f'denver_bldg_{building_id:03d}',
                'yearbuilt': yearbuilt,
                'strtype': strtype,
                'occtype': occtype,
                'stories': stories,
                'bldgarea': bldgarea,
                'arch_flood': arch_flood,
                'ffe_elev': ffe_elev,
                'geometry': Point(lon, lat)
            }
            
            buildings.append(building)
            building_id += 1
    
    return buildings

def create_shapefile(output_path=None):
    """Create the shapefile and save it as a zip."""
    # Generate buildings
    buildings = generate_buildings()
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(buildings, crs='EPSG:4326')
    
    # Determine output directory
    if output_path is None:
        output_path = os.getcwd()
    
    # Create temporary directory for shapefile
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        # Save shapefile
        shp_path = os.path.join(temp_dir, 'denver_realistic_buildings')
        gdf.to_file(shp_path)
        
        # Create zip file
        zip_path = os.path.join(output_path, 'Denver_Realistic_Buildings.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Find the actual directory where geopandas saved the files
            if os.path.isdir(shp_path):
                shp_dir = shp_path
            else:
                shp_dir = temp_dir
            
            # Add all shapefile components
            for f in os.listdir(shp_dir):
                if f.startswith('denver_realistic_buildings') and f.endswith(('.shp', '.shx', '.dbf', '.prj', '.cpg')):
                    file_path = os.path.join(shp_dir, f)
                    zipf.write(file_path, f)
    
    # Print summary
    print(f"Created shapefile with {len(gdf)} buildings")
    print(f"\nBuilding type distribution:")
    print(gdf['occtype'].value_counts())
    print(f"\nStructure type distribution:")
    print(gdf['strtype'].value_counts())
    print(f"\nStories distribution:")
    print(gdf['stories'].value_counts().sort_index())
    print(f"\nYear built range: {gdf['yearbuilt'].min()} - {gdf['yearbuilt'].max()}")
    print(f"\nBuilding area range: {gdf['bldgarea'].min()} - {gdf['bldgarea'].max()} sq ft")
    print(f"\nFlood risk distribution:")
    print(gdf['arch_flood'].value_counts().sort_index())
    print(f"\nGeometry bounds:")
    bounds = gdf.total_bounds
    print(f"  Min Lon: {bounds[0]:.4f}, Max Lon: {bounds[2]:.4f}")
    print(f"  Min Lat: {bounds[1]:.4f}, Max Lat: {bounds[3]:.4f}")
    
    print(f"\n✓ Building dataset created: {zip_path}")
    print("\nThis dataset includes:")
    print("- 50 buildings distributed across 4 distinct urban clusters")
    print("- Downtown high-density area with office and residential towers")
    print("- Northern residential neighborhood with single and multi-family homes")
    print("- Western industrial corridor with warehouses and factories")
    print("- Southern suburban area with scattered development")
    print("\nThe dataset is compatible with the building upload endpoint.")
    
    return zip_path

if __name__ == "__main__":
    create_shapefile()