#!/usr/bin/env python3
"""Examine the structure of the existing Denver buildings shapefile."""

import geopandas as gpd
import pandas as pd
import os

# Copy the shapefile from seed_data
shp_path = "/app/app/seed_data/buildings/denver_test_buildings_manual.shp"

# First extract the zip file
import zipfile
zip_path = "/app/app/seed_data/buildings/Denver Buildings.zip"
extract_path = "/app/data/temp_extract"
os.makedirs(extract_path, exist_ok=True)

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_path)

# Now read the shapefile
shp_path = os.path.join(extract_path, "buildings_zip/denver_test_buildings_manual.shp")
gdf = gpd.read_file(shp_path)

print("Shapefile structure:")
print(f"Number of features: {len(gdf)}")
print(f"CRS: {gdf.crs}")
print("\nColumns:")
print(gdf.columns.tolist())
print("\nData types:")
print(gdf.dtypes)
print("\nFirst 5 rows:")
print(gdf.head())
print("\nSample values from each column:")
for col in gdf.columns:
    if col != 'geometry':
        print(f"\n{col}:")
        print(f"  Sample values: {gdf[col].head(10).tolist()}")
        print(f"  Unique count: {gdf[col].nunique()}")

# Show geometry bounds
bounds = gdf.total_bounds
print(f"\nGeometry bounds:")
print(f"  Min X (lon): {bounds[0]}")
print(f"  Min Y (lat): {bounds[1]}")
print(f"  Max X (lon): {bounds[2]}")
print(f"  Max Y (lat): {bounds[3]}")

# Clean up
import shutil
shutil.rmtree(extract_path)