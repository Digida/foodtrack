"""Entry point for seeding the database with reference data."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_food_items import seed

if __name__ == "__main__":
    asyncio.run(seed())
