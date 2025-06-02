"""
Seed data loader for initial database population.
Loads data from /app/seed_data on startup if not already present.
Uses API endpoints to ensure proper validation and processing.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import httpx

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Hazard, FragilityCurve, MappingSet, BuildingDataset, Intervention

logger = logging.getLogger(__name__)

SEED_DATA_DIR = Path("/app/seed_data")
BASE_URL = "http://localhost:8000"  # Internal API calls


async def check_data_exists(session: AsyncSession) -> dict[str, bool]:
    """Check which types of data already exist in the database."""
    results = {}
    
    # Check for hazards
    hazard_result = await session.execute(select(Hazard).limit(1))
    results['hazards'] = hazard_result.scalar() is not None
    
    # Check for fragility curves
    fragility_result = await session.execute(select(FragilityCurve).limit(1))
    results['fragility_curves'] = fragility_result.scalar() is not None
    
    # Check for mapping sets
    mapping_result = await session.execute(select(MappingSet).limit(1))
    results['mapping_sets'] = mapping_result.scalar() is not None
    
    # Check for building datasets
    building_result = await session.execute(select(BuildingDataset).limit(1))
    results['building_datasets'] = building_result.scalar() is not None
    
    # Check for interventions
    intervention_result = await session.execute(select(Intervention).limit(1))
    results['interventions'] = intervention_result.scalar() is not None
    
    return results


async def seed_hazards_via_api(client: httpx.AsyncClient) -> None:
    """Seed hazard data using the API endpoint."""
    hazards_dir = SEED_DATA_DIR / "hazards"
    if not hazards_dir.exists():
        logger.warning(f"Hazards seed directory not found: {hazards_dir}")
        return
    
    for tif_file in hazards_dir.glob("*.tif"):
        with open(tif_file, 'rb') as f:
            files = {
                "wse_raster": (tif_file.name, f, "image/tiff")
            }
            data = {
                "name": f"{tif_file.stem.replace('_', ' ').title()}"
            }
            
            response = await client.post(
                f"{BASE_URL}/hazards",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                logger.info(f"Seeded hazard: {tif_file.name}")
            else:
                logger.error(f"Failed to seed hazard {tif_file.name}: {response.text}")


async def seed_fragility_curves_via_api(client: httpx.AsyncClient) -> None:
    """Seed fragility curve data using the API endpoint."""
    fragility_dir = SEED_DATA_DIR / "fragility_curves"
    if not fragility_dir.exists():
        logger.warning(f"Fragility curves seed directory not found: {fragility_dir}")
        return
    
    for json_file in fragility_dir.glob("*.json"):
        # Read the JSON to get the ID for the name
        with open(json_file, 'r') as f:
            data = json.load(f)
            curve_id = data.get('id', json_file.stem)
        
        with open(json_file, 'rb') as f:
            files = {
                "fragility_json": (json_file.name, f, "application/json")
            }
            data = {
                "name": curve_id
            }
            
            response = await client.post(
                f"{BASE_URL}/fragility-curves",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                logger.info(f"Seeded fragility curve: {json_file.name}")
            else:
                logger.error(f"Failed to seed fragility curve {json_file.name}: {response.text}")


async def seed_mapping_sets_via_api(client: httpx.AsyncClient) -> None:
    """Seed mapping set data using the API endpoint."""
    mapping_dir = SEED_DATA_DIR / "mapping_sets"
    if not mapping_dir.exists():
        logger.warning(f"Mapping sets seed directory not found: {mapping_dir}")
        return
    
    for json_file in mapping_dir.glob("*.json"):
        with open(json_file, 'rb') as f:
            files = {
                "mapping_json": (json_file.name, f, "application/json")
            }
            data = {
                "name": f"{json_file.stem.replace('_', ' ').title()}"
            }
            
            response = await client.post(
                f"{BASE_URL}/mapping-sets",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                logger.info(f"Seeded mapping set: {json_file.name}")
            else:
                logger.error(f"Failed to seed mapping set {json_file.name}: {response.text}")


async def seed_building_datasets_via_api(client: httpx.AsyncClient) -> None:
    """Seed building dataset data using the API endpoint."""
    buildings_dir = SEED_DATA_DIR / "buildings"
    if not buildings_dir.exists():
        logger.warning(f"Buildings seed directory not found: {buildings_dir}")
        return
    
    for zip_file in buildings_dir.glob("*.zip"):
        with open(zip_file, 'rb') as f:
            files = {
                "shapefile_zip": (zip_file.name, f, "application/zip")
            }
            data = {
                "name": f"{zip_file.stem.replace('_', ' ').title()}"
            }
            
            response = await client.post(
                f"{BASE_URL}/datasets/buildings",
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                dataset = response.json()
                logger.info(f"Seeded building dataset: {zip_file.name} with {dataset.get('feature_count', 0)} buildings")
                
                # Optionally set some default asset values for the first few buildings
                if dataset.get('id'):
                    await set_sample_asset_values(client, dataset['id'])
            else:
                logger.error(f"Failed to seed building dataset {zip_file.name}: {response.text}")


async def set_sample_asset_values(client: httpx.AsyncClient, dataset_id: int) -> None:
    """Set sample asset values for some buildings in the dataset."""
    # Get buildings
    response = await client.get(f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings")
    if response.status_code != 200:
        return
    
    buildings = response.json()[:20]  # Just the first 20 buildings
    
    # Create sample asset values based on building properties
    bulk_updates = {}
    for i, building in enumerate(buildings):
        # Simple formula for demo purposes
        # In reality, this could be based on building type, size, etc.
        base_value = 500000
        properties = building.get('properties', {})
        
        # Adjust based on number of stories if available
        stories = properties.get('stories', 1)
        try:
            stories = float(stories)
            base_value = base_value * (1 + (stories - 1) * 0.5)
        except:
            pass
        
        bulk_updates[building['guid']] = base_value + (i * 25000)
    
    # Update asset values
    if bulk_updates:
        response = await client.post(
            f"{BASE_URL}/datasets/buildings/{dataset_id}/buildings/bulk-update-assets",
            json=bulk_updates
        )
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Set asset values for {result['updated']} sample buildings")


async def seed_interventions_via_api(client: httpx.AsyncClient) -> None:
    """Seed intervention types using the API endpoint."""
    interventions = [
        {
            "name": "Building Elevation",
            "type": "building_elevation",
            "description": "Elevate the building structure to reduce flood risk"
        },
    ]
    
    for intervention_data in interventions:
        response = await client.post(
            f"{BASE_URL}/interventions",
            json=intervention_data
        )
        
        if response.status_code == 200:
            logger.info(f"Seeded intervention: {intervention_data['name']}")
        else:
            logger.error(f"Failed to seed intervention {intervention_data['name']}: {response.text}")


async def seed_database() -> None:
    """Main seeding function that checks and seeds data as needed."""
    logger.info("Checking for seed data...")
    
    async for session in get_async_session():
        try:
            # Check what data already exists
            existing = await check_data_exists(session)
            
            # Use API client for seeding
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Seed missing data
                if not existing['hazards']:
                    logger.info("Seeding hazards...")
                    await seed_hazards_via_api(client)
                else:
                    logger.info("Hazards already exist, skipping seed")
                
                if not existing['fragility_curves']:
                    logger.info("Seeding fragility curves...")
                    await seed_fragility_curves_via_api(client)
                else:
                    logger.info("Fragility curves already exist, skipping seed")
                
                if not existing['mapping_sets']:
                    logger.info("Seeding mapping sets...")
                    await seed_mapping_sets_via_api(client)
                else:
                    logger.info("Mapping sets already exist, skipping seed")
                
                if not existing['building_datasets']:
                    logger.info("Seeding building datasets...")
                    await seed_building_datasets_via_api(client)
                else:
                    logger.info("Building datasets already exist, skipping seed")
                
                if not existing['interventions']:
                    logger.info("Seeding interventions...")
                    await seed_interventions_via_api(client)
                else:
                    logger.info("Interventions already exist, skipping seed")
            
            logger.info("Seeding complete!")
            
        except httpx.ConnectError:
            logger.error("Cannot connect to API. Server may not be fully started yet.")
            # This is expected during startup - the server starts after this runs
        except Exception as e:
            logger.error(f"Error during seeding: {e}")
            raise
        finally:
            await session.close()


def run_seed_sync() -> None:
    """Synchronous wrapper for the async seed function."""
    asyncio.run(seed_database()) 