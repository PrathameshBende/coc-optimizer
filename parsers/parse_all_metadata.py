"""
Simple metadata parser stub for optimizer
Loads all *.json files in the provided data directory and returns combined list.
"""

import json
from pathlib import Path
from typing import List, Any

def parse_all_metadata(data_dir: Path) -> List[Any]:
    """Parse all JSON metadata files in the data directory.
    Returns a list of metadata objects (dicts)."""
    metadata = []
    if not isinstance(data_dir, Path):
        data_dir = Path(data_dir)
    
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    for json_file in data_dir.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Assume each file contains a list of metadata items
                if isinstance(data, list):
                    metadata.extend(data)
                else:
                    metadata.append(data)
        except Exception as e:
            # Skip invalid files but log
            print(f"Failed to parse {json_file}: {e}")
    
    return metadata
