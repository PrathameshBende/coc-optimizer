# optimizer/parsers/__init__.py
from pathlib import Path
from models import NormalizedTaskMetadata
from parsers.builder_parser import parse_builder_metadata
from parsers.lab_parser import parse_lab_metadata
from parsers.pet_parser import parse_pet_metadata

def parse_all_metadata(base_data_dir: Path) -> list[NormalizedTaskMetadata]:
    """Scans the data directory and returns all normalized metadata."""
    metadata = []
    metadata.extend(parse_builder_metadata(base_data_dir))
    metadata.extend(parse_lab_metadata(base_data_dir))
    metadata.extend(parse_pet_metadata(base_data_dir))
    return metadata