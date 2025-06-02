#!/usr/bin/env python3
"""
Test script to demonstrate building dataset upload with asset value assignment.

Usage:
    docker-compose exec backend python scripts/test_building_upload.py
"""

import asyncio
import httpx
from pathlib import Path

BASE_URL = "http://localhost:8000"


async def main():
    async with httpx.AsyncClient() as client:
        # 1. Upload a building dataset
        print("1. Uploading building dataset...")
        
        # Use existing shapefile zip
        sample_zip = Path("/data/building_buildings_zip.zip")
        if not sample_zip.exists():
            print(f"Sample zip not found at {sample_zip}")
            return
        
        with open(sample_zip, "rb") as f:
            files = {"shapefile_zip": ("buildings.zip", f, "application/zip")}
            data = {"name": "Test Buildings with Asset Values"}
            
            response = await client.post(
                f"{BASE_URL}/datasets/buildings",
                files=files,
                data=data
            )
        
        if response.status_code != 200:
            print(f"Failed to upload dataset: {response.text}")
            return
        
        dataset = response.json()
        dataset_id = dataset["id"]
        print(f"✓ Dataset uploaded with ID: {dataset_id}")
        print(f"  Feature count: {dataset.get('feature_count', 'Unknown')}")
        
        # 2. List buildings in the dataset
        print("\n2. Fetching buildings...")
        response = await client.get(f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings")
        
        if response.status_code != 200:
            print(f"Failed to fetch buildings: {response.text}")
            return
        
        buildings = response.json()
        print(f"✓ Found {len(buildings)} buildings")
        
        # Show first 5 buildings
        print("\nFirst 5 buildings:")
        for i, building in enumerate(buildings[:5]):
            print(f"  - GUID: {building['guid']}")
            print(f"    Properties: {list(building['properties'].keys())[:5]}...")  # Show first 5 properties
            print(f"    Asset Value: ${building['asset_value'] or 'Not set'}")
        
        # 3. Update asset values for some buildings
        print("\n3. Setting asset values...")
        
        # Individual update
        if buildings:
            first_building = buildings[0]
            response = await client.patch(
                f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings/{first_building['guid']}",
                params={"asset_value": 500000}
            )
            
            if response.status_code == 200:
                print(f"✓ Updated building {first_building['guid']} with asset value $500,000")
        
        # Bulk update
        bulk_updates = {}
        for i, building in enumerate(buildings[:10]):
            # Assign values based on building properties (if available)
            # For demo, just use a formula
            bulk_updates[building['guid']] = 100000 + (i * 50000)
        
        response = await client.post(
            f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings/bulk-update-assets",
            json=bulk_updates
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Bulk updated {result['updated']} buildings")
        
        # 4. Verify updates
        print("\n4. Verifying updates...")
        response = await client.get(f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings")
        
        if response.status_code == 200:
            buildings = response.json()
            buildings_with_values = [b for b in buildings if b['asset_value'] is not None]
            print(f"✓ {len(buildings_with_values)} buildings now have asset values")
            
            # Show updated buildings
            print("\nUpdated buildings:")
            for building in buildings[:5]:
                if building['asset_value'] is not None:
                    print(f"  - GUID: {building['guid']}, Asset Value: ${building['asset_value']:,.0f}")


if __name__ == "__main__":
    asyncio.run(main()) 