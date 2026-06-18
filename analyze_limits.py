# optimizer/analyze_limits.py
import json
import sys
from pathlib import Path
from collections import Counter

from parsers import parse_all_metadata
from task_generator import parse_export_state, get_infra_levels, get_instances, get_max_possible_infra_levels
from models import ResourceType

def analyze(export_path: str, data_dir: str):
    print(f"📂 Loading metadata...")
    metadata = parse_all_metadata(Path(data_dir))
    
    print(f"📜 Loading village export...")
    with open(export_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)
        
    state = parse_export_state(export_data)
    current_infra = get_infra_levels(state, metadata)
    max_infra = get_max_possible_infra_levels(state, metadata, current_infra)  # FIX: Calculate max possible
    
    print(f"\n🏗️ Current Infrastructure:")
    print(f"  Town Hall  : Level {current_infra['TH']}")
    print(f"  Hero Hall  : Level {current_infra['HeroHall']} → {max_infra['HeroHall']} (max possible)")
    print(f"  Laboratory : Level {current_infra['Lab']} → {max_infra['Lab']} (max possible)")
    print(f"  Pet House  : Level {current_infra['PetHouse']} → {max_infra['PetHouse']} (max possible)")
    
    print(f"\n{'='*85}")
    print(f"{'Name':<25} {'Type':<10} {'Current':<15} {'Max Possible':<13} {'Time to Max (Hours)':<15}")
    print(f"{'='*85}")
    
    totals = {ResourceType.BUILDER: 0.0, ResourceType.LAB: 0.0, ResourceType.PET: 0.0}
    
    for item in metadata:
        if item.name == "Town Hall":  # FIX: Skip Town Hall
            continue
            
        instances = get_instances(state, int(item.data_id))
        
        max_count = 1
        if item.resource == ResourceType.BUILDER and item.count_by_th:
            max_count = item.count_by_th.get(current_infra["TH"], 1)
            
        while len(instances) < max_count:
            instances.append(0)
            
        if not instances:
            continue

        total_time_for_item = 0.0
        max_possible_lvl_for_item = 0
        min_current_lvl = min(instances)
        
        for start_lvl in instances:
            current_max_lvl = start_lvl
            time_for_this_instance = 0.0
            
            for level_meta in item.levels:
                if level_meta.level <= start_lvl:
                    continue
                
                # FIX: Use max_infra for ceiling checks
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]:
                    break
                if level_meta.hero_hall_required and level_meta.hero_hall_required > max_infra["HeroHall"]:
                    break
                if level_meta.lab_required and level_meta.lab_required > max_infra["Lab"]:
                    break
                if level_meta.pet_house_required and level_meta.pet_house_required > max_infra["PetHouse"]:
                    break
                    
                current_max_lvl = level_meta.level
                time_for_this_instance += level_meta.duration_seconds / 3600
                
            total_time_for_item += time_for_this_instance
            if current_max_lvl > max_possible_lvl_for_item:
                max_possible_lvl_for_item = current_max_lvl
                
        totals[item.resource] += total_time_for_item
        
        if max_possible_lvl_for_item > min_current_lvl:
            if len(set(instances)) == 1:
                current_str = str(instances[0])
            else:
                counts = Counter(instances)
                current_str = ", ".join(f"{cnt}xL{lvl}" for lvl, cnt in sorted(counts.items()))
                
            print(f"{item.name:<25} {item.resource.value:<10} {current_str:<15} {max_possible_lvl_for_item:<13} {total_time_for_item:<15.1f}")

    print(f"{'='*85}")
    print(f"\n📊 TOTAL WORKLOAD SUMMARY:")
    print(f"  Builder Work : {totals[ResourceType.BUILDER]:.1f} hours ({totals[ResourceType.BUILDER]/24:.1f} days)")
    print(f"  Lab Work     : {totals[ResourceType.LAB]:.1f} hours ({totals[ResourceType.LAB]/24:.1f} days)")
    print(f"  Pet Work     : {totals[ResourceType.PET]:.1f} hours ({totals[ResourceType.PET]/24:.1f} days)")
    
    print(f"\n🧮 THEORETICAL MINIMUM MAKESPAN (Total Work / Machines):")
    print(f"  Builders (5) : {totals[ResourceType.BUILDER] / (5 * 24):.1f} days")
    print(f"  Lab (1)      : {totals[ResourceType.LAB] / (1 * 24):.1f} days")
    print(f"  Pets (1)     : {totals[ResourceType.PET] / (1 * 24):.1f} days")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_limits.py <path_to_export.json> [path_to_data_dir]")
        sys.exit(1)
        
    export_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/zorro/Projects/optimizer/clash-of-clans-data/data/home"
    
    analyze(export_path, data_dir)