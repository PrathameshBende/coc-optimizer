# optimizer/parsers/builder_parser.py
import json
from pathlib import Path
from models import NormalizedTaskMetadata, NormalizedLevel, ResourceType
from parsers.utils import extract_duration, parse_count_by_th, load_json_clean

BUILDER_DIRS = [
    "army-buildings", "defenses", "resource-buildings", 
    "traps", "walls", "other", "town-hall", "heroes"
]

def parse_builder_metadata(base_dir: Path) -> list[NormalizedTaskMetadata]:
    metadata_list = []

    for dir_name in BUILDER_DIRS:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            continue

        for file_path in dir_path.glob("*.json"):
            try:
                data = load_json_clean(file_path)

                data_id = data.get("dataId", file_path.stem)
                name = data.get("name", data_id)
                
                raw_counts = data.get("availablePerTownHall")
                count_by_th = parse_count_by_th(raw_counts)

                levels = []
                for raw_level in data.get("levels", []):
                    duration = extract_duration(raw_level.get("buildTime") or raw_level.get("upgradeTime"))
                    if duration is None:
                        continue

                    levels.append(NormalizedLevel(
                        level=raw_level["level"],
                        duration_seconds=duration,
                        town_hall_required=raw_level.get("townHallRequired"),
                        hero_hall_required=raw_level.get("heroHallLevelRequired"),
                        supercharge=bool(raw_level.get("supercharge", False))
                    ))

                if levels:
                    metadata_list.append(NormalizedTaskMetadata(
                        data_id=data_id,
                        name=name,
                        resource=ResourceType.BUILDER,
                        count_by_th=count_by_th,
                        levels=levels
                    ))
            except Exception as e:
                print(f"⚠️  Error parsing {file_path}: {e}")
                continue

    return metadata_list