import json
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
VEHICLE_CLICK_FILEPATH = CURRENT_DIR / "VehicleRace.json"

with open(VEHICLE_CLICK_FILEPATH, "r", encoding="utf-8") as f:
    VEHICLE_CLICK_DATA = json.load(f)

__all__ = ["VEHICLE_CLICK_DATA"]
