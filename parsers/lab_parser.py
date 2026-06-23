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
                
                # Extract root requirements
                root_spell_factory_req = data.get("spellFactoryLevelRequired")
                root_workshop_req = data.get("workshopLevelRequired")
                root_barrack_req = data.get("barrackLevelRequired")
                
                # Extract types to map requirements correctly
                troop_type = data.get("troopType", "regular")
                spell_type = data.get("spellType", "regular")

                levels = []
                for raw_level in data.get("levels", []):
                    duration = extract_duration(raw_level.get("researchTime"))
                    if duration is None:
                        continue

                    # Map Spell Factory vs Dark Spell Factory
                    sf_req = root_spell_factory_req if spell_type == "regular" else None
                    dsf_req = root_spell_factory_req if spell_type == "dark" else None
                    
                    # Map Barracks vs Dark Barracks
                    barr_req = root_barrack_req if troop_type == "regular" else None
                    dark_barr_req = root_barrack_req if troop_type == "dark" else None

                    levels.append(NormalizedLevel(
                        level=raw_level["level"],
                        duration_seconds=duration,
                        town_hall_required=raw_level.get("townHallRequired"),
                        lab_required=raw_level.get("laboratoryRequired"),
                        spell_factory_required=sf_req,
                        dark_spell_factory_required=dsf_req,
                        workshop_required=root_workshop_req,
                        barracks_required=barr_req,
                        dark_barracks_required=dark_barr_req
                    ))

                if levels:
                    metadata_list.append(NormalizedTaskMetadata(
                        data_id=data_id, name=name, resource=ResourceType.LAB, levels=levels
                    ))
            except Exception as e:
                print(f"⚠️  Error parsing {file_path}: {e}")
                continue

    return metadata_list