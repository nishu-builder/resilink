#!/usr/bin/env python3
"""
Manual database seeding script.

Usage:
    docker-compose exec backend python scripts/seed_database.py
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.seed import seed_database


async def main():
    """Run the seeding process."""
    print("Starting manual database seeding...")
    await seed_database()
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(main()) 