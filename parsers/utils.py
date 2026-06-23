# optimizer/parsers/utils.py
import json
from pathlib import Path
from typing import Optional, Any  # <-- ADD THIS LINE

def load_json_clean(file_path: Path) -> dict[str, Any]:
    """Loads JSON and strips whitespace from all keys and string values."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # FIX: Add type hints to the recursive function
    def strip_obj(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k.strip(): strip_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [strip_obj(item) for item in obj]
        elif isinstance(obj, str):
            return obj.strip()
        return obj
        
    return strip_obj(raw_data)

def extract_duration(raw_time) -> Optional[int]:
    """Extracts duration in seconds from various formats."""
    if raw_time is None:
        return None
    if isinstance(raw_time, int):
        return raw_time
    if isinstance(raw_time, dict):
        days = int(raw_time.get("days", 0) or 0)
        hours = int(raw_time.get("hours", 0) or 0)
        minutes = int(raw_time.get("minutes", 0) or 0)
        seconds = int(raw_time.get("seconds", 0) or 0)
        total = (days * 86400) + (hours * 3600) + (minutes * 60) + seconds
        return total if total > 0 else None
    return None

def parse_count_by_th(raw_counts) -> Optional[dict[int, int]]:
    """Safely parse availablePerTownHall into {TH_level: count}."""
    if not raw_counts:
        return None
    
    result: dict[int, int] = {}
    
    if isinstance(raw_counts, list):
        for item in raw_counts:
            if isinstance(item, dict):
                th = item.get("townHallLevel")
                count = item.get("count")
                if th is not None and count is not None:
                    result[int(th)] = int(count)
    elif isinstance(raw_counts, dict):
        for k, v in raw_counts.items():
            if k in ["townHallLevel", "level"]:
                continue
            try:
                th = int(k)
                if isinstance(v, dict):
                    count = v.get("count")
                    if count:
                        result[th] = int(count)
                elif isinstance(v, (int, float)) and v > 0:
                    result[th] = int(v)
            except (ValueError, TypeError):
                pass
                
    return result if result else None