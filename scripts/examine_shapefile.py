#!/usr/bin/env python3
"""Examine the structure of the existing Denver buildings shapefile."""

import geopandas as gpd
import pandas as pd

# Read the shapefile
shp_path = "/Users/nishadsingh/repos/incore-explore/hazard/data/buildings_zip/denver_test_buildings_manual.shp"
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
print("\nUnique values in key columns:")
for col in gdf.columns:
    if col != 'geometry':
        unique_vals = gdf[col].unique()
        if len(unique_vals) <= 20:
            print(f"\n{col}: {unique_vals}")
        else:
            print(f"\n{col}: {len(unique_vals)} unique values (showing first 10)")
            print(unique_vals[:10])