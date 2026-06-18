# optimizer/parsers/pet_parser.py
import json
from pathlib import Path
from models import NormalizedTaskMetadata, NormalizedLevel, ResourceType
from parsers.utils import extract_duration, load_json_clean

PET_DIRS = ["pets"]

def parse_pet_metadata(base_dir: Path) -> list[NormalizedTaskMetadata]:
    metadata_list = []

    for dir_name in PET_DIRS:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.glob("*.json"):
            try:
                data = load_json_clean(file_path)

                data_id = data.get("dataId", file_path.stem)
                name = data.get("name", data_id)

                levels = []
                for raw_level in data.get("levels", []):
                    duration = extract_duration(raw_level.get("upgradeTime"))
                    if duration is None:
                        continue

                    levels.append(NormalizedLevel(
                        level=raw_level["level"],
                        duration_seconds=duration,
                        town_hall_required=raw_level.get("townHallRequired"),
                        pet_house_required=raw_level.get("petHouseLevelRequired")
                    ))

                if levels:
                    metadata_list.append(NormalizedTaskMetadata(
                        data_id=data_id,
                        name=name,
                        resource=ResourceType.PET,
                        levels=levels
                    ))
            except Exception as e:
                print(f"⚠️  Error parsing {file_path}: {e}")
                continue

    return metadata_list