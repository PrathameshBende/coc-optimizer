# optimizer/validate_schedule.py
import json
import sys
from pathlib import Path

from parsers import parse_all_metadata
from task_generator import generate_tasks, parse_export_state, get_infra_levels
from exact_scheduler import solve_exact
from models import ResourceType

MACHINE_COUNTS = {
    ResourceType.BUILDER: 5,
    ResourceType.LAB: 1,
    ResourceType.PET: 1
}

def validate(export_path: str, data_dir: str):
    print("📂 Loading metadata...")
    metadata = parse_all_metadata(Path(data_dir))
    metadata_map = {int(m.data_id): m for m in metadata}
    
    print("📜 Loading village export...")
    with open(export_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)
        
    print("⚙️  Generating tasks...")
    all_tasks = generate_tasks(export_data, metadata)
    
    print("🚀 Running Unified Solver...")
    schedules = solve_exact(MACHINE_COUNTS, all_tasks, time_limit_seconds=120)
    
    # Create a lookup for the schedule
    schedule_map = {s.task_id: s for s in schedules}
    
    # Get current infrastructure levels from the export
    state = parse_export_state(export_data)
    current_infra = get_infra_levels(state, metadata)
    
    # Map infrastructure names to their Data IDs
    infra_data_ids = {}
    for m in metadata:
        if m.name in ["Town Hall", "Laboratory", "Pet House", "Spell Factory", 
                      "Dark Spell Factory", "Workshop", "Barracks", "Dark Barracks", "Hero Hall"]:
            infra_data_ids[m.name] = int(m.data_id)
            
    print("\n" + "="*60)
    print(" 🔍 VALIDATING SCHEDULE")
    print("="*60)
    
    violations = 0
    
    for s in schedules:
        task_id = s.task_id
        parts = task_id.split('_')
        data_id = int(parts[0])
        level = int(parts[1])
        instance_idx = int(parts[2])
        start_time = s.start_time
        
        meta = metadata_map.get(data_id)
        if not meta: continue
            
        level_meta = next((l for l in meta.levels if l.level == level), None)
        if not level_meta: continue
            
        # 1. Check previous level dependency (Sequential Upgrades)
        if level > 1:
            prev_task_id = f"{data_id}_{level - 1}_{instance_idx}"
            prev_s = schedule_map.get(prev_task_id)
            if prev_s and prev_s.end_time > start_time:
                print(f"❌ VIOLATION: {meta.name} L{level} starts at {start_time//3600}h, but L{level-1} finishes at {prev_s.end_time//3600}h!")
                violations += 1
                
        # 2. Check infrastructure dependencies
        requirements = {
            "Town Hall": level_meta.town_hall_required,
            "Laboratory": level_meta.lab_required,
            "Pet House": level_meta.pet_house_required,
            "Hero Hall": level_meta.hero_hall_required,
            "Spell Factory": level_meta.spell_factory_required,
            "Dark Spell Factory": level_meta.dark_spell_factory_required,
            "Workshop": level_meta.workshop_required,
            "Barracks": level_meta.barracks_required,
            "Dark Barracks": level_meta.dark_barracks_required,
        }
        
        infra_key_map = {
            "Town Hall": "TH", "Laboratory": "Lab", "Pet House": "PetHouse", 
            "Hero Hall": "HeroHall", "Spell Factory": "SF", "Dark Spell Factory": "DSF", 
            "Workshop": "Workshop", "Barracks": "Barracks", "Dark Barracks": "DarkBarracks"
        }
        
        for infra_name, req_level in requirements.items():
            if req_level is None: continue
            
            infra_key = infra_key_map[infra_name]
            current_level = current_infra.get(infra_key, 1)
            
            # If the infrastructure is already at or above the required level, no dependency is needed
            if req_level <= current_level: continue
                
            infra_id = infra_data_ids.get(infra_name)
            if not infra_id: continue
                
            # Look for the specific infrastructure upgrade task in the schedule
            dep_task_id = f"{infra_id}_{req_level}_0"
            dep_s = schedule_map.get(dep_task_id)
            
            if dep_s is None:
                print(f"❌ VIOLATION: {meta.name} L{level} requires {infra_name} L{req_level}, but upgrade task not found in schedule!")
                violations += 1
            elif dep_s.end_time > start_time:
                print(f"❌ VIOLATION: {meta.name} L{level} starts at {start_time//3600}h, but {infra_name} L{req_level} finishes at {dep_s.end_time//3600}h!")
                violations += 1

    print("\n" + "="*60)
    if violations == 0:
        print("✅ VALIDATION PASSED: All prerequisites are perfectly respected!")
        print("   The CP-SAT solver is mathematically respecting all dependencies.")
    else:
        print(f"❌ VALIDATION FAILED: Found {violations} violations.")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_schedule.py <path_to_export.json> [path_to_data_dir]")
        sys.exit(1)
        
    export_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/zorro/Projects/optimizer/clash-of-clans-data/data/home"
    
    validate(export_path, data_dir)