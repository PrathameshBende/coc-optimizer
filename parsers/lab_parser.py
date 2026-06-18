# optimizer/parsers/lab_parser.py
import json
from pathlib import Path
from models import NormalizedTaskMetadata, NormalizedLevel, ResourceType
from parsers.utils import extract_duration, load_json_clean

LAB_DIRS = ["troops", "spells", "siege-machines"]

def parse_lab_metadata(base_dir: Path) -> list[NormalizedTaskMetadata]:
    metadata_list = []

    for dir_name in LAB_DIRS:
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
                    duration = extract_duration(raw_level.get("researchTime"))
                    if duration is None:
                        continue

                    levels.append(NormalizedLevel(
                        level=raw_level["level"],
                        duration_seconds=duration,
                        town_hall_required=raw_level.get("townHallRequired"),
                        lab_required=raw_level.get("laboratoryRequired")
                    ))

                if levels:
                    metadata_list.append(NormalizedTaskMetadata(
                        data_id=data_id,
                        name=name,
                        resource=ResourceType.LAB,
                        levels=levels
                    ))
            except Exception as e:
                print(f"⚠️  Error parsing {file_path}: {e}")
                continue

    return metadata_list