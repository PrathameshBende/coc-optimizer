# optimizer/task_generator.py
import json
from pathlib import Path
from models import Task, NormalizedTaskMetadata, ResourceType

def parse_export_state(export_data: dict) -> dict:
    state = {
        "buildings": {}, "units": {}, "heroes": {}, 
        "spells": {}, "siege_machines": {}, "pets": {},
        "traps": {}  # FIX: Add traps
    }
    
    def process_list(key, items):
        for item in items:
            data_id = item["data"]
            lvl = item.get("lvl", 0)
            cnt = item.get("cnt", 1)
            timer = item.get("timer", 0)
            
            if data_id not in state[key]:
                state[key][data_id] = {"levels": {}, "timer": 0}
            
            state[key][data_id]["levels"][lvl] = state[key][data_id]["levels"].get(lvl, 0) + cnt
            if timer > 0:
                state[key][data_id]["timer"] = timer 

    process_list("buildings", export_data.get("buildings", []) + export_data.get("buildings2", []))
    process_list("units", export_data.get("units", []) + export_data.get("units2", []))
    process_list("heroes", export_data.get("heroes", []) + export_data.get("heroes2", []))
    process_list("spells", export_data.get("spells", []))
    process_list("siege_machines", export_data.get("siege_machines", []))
    process_list("pets", export_data.get("pets", []))
    process_list("traps", export_data.get("traps", []) + export_data.get("traps2", []))  # FIX: Process traps
    
    return state

def get_infra_levels(state: dict, metadata: list[NormalizedTaskMetadata]) -> dict:
    infra = {"TH": 1, "Lab": 1, "PetHouse": 1, "HeroHall": 1, "Blacksmith": 1}
    name_map = {
        "Town Hall": "TH", "Laboratory": "Lab", "Pet House": "PetHouse", 
        "Hero Hall": "HeroHall", "Blacksmith": "Blacksmith"
    }
    for task in metadata:
        if task.name in name_map and task.resource == ResourceType.BUILDER:
            key = name_map[task.name]
            instances = get_instances(state, int(task.data_id))
            if instances:
                infra[key] = max(instances)
    return infra

def get_max_possible_infra_levels(state: dict, metadata: list[NormalizedTaskMetadata], current_infra: dict) -> dict:
    """Calculate the maximum possible level for each infrastructure building."""
    max_infra = current_infra.copy()
    
    for task in metadata:
        if task.name in ["Town Hall", "Laboratory", "Pet House", "Hero Hall", "Blacksmith"]:
            instances = get_instances(state, int(task.data_id))
            current_lvl = max(instances) if instances else 0
            
            max_lvl = current_lvl
            for level_meta in task.levels:
                if level_meta.level <= current_lvl:
                    continue
                # Check TH ceiling
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]:
                    break
                max_lvl = level_meta.level
            
            if task.name == "Hero Hall":
                max_infra["HeroHall"] = max_lvl
            elif task.name == "Laboratory":
                max_infra["Lab"] = max_lvl
            elif task.name == "Pet House":
                max_infra["PetHouse"] = max_lvl
    
    return max_infra

def get_instances(state: dict, data_id: int) -> list[int]:
    """Returns a list of current levels for every instance of a building/unit."""
    for category in ["buildings", "units", "heroes", "spells", "siege_machines", "pets", "traps"]:  # FIX: Add traps
        if data_id in state[category]:
            levels_dict = state[category][data_id]["levels"]
            instances = []
            for lvl, cnt in levels_dict.items():
                instances.extend([lvl] * cnt)
            return instances
    return []

def generate_tasks(export_data: dict, metadata: list[NormalizedTaskMetadata]) -> list[Task]:
    state = parse_export_state(export_data)
    current_infra = get_infra_levels(state, metadata)
    max_infra = get_max_possible_infra_levels(state, metadata, current_infra)  # FIX: Calculate max possible infra
    
    infra_names = {"Town Hall", "Laboratory", "Hero Hall", "Pet House"}
    infra_items = [m for m in metadata if m.name in infra_names]
    regular_items = [m for m in metadata if m.name not in infra_names and m.name != "Town Hall"]  # FIX: Exclude Town Hall
    
    hero_hall_id = next((m.data_id for m in metadata if m.name == "Hero Hall"), None)
    pet_house_id = next((m.data_id for m in metadata if m.name == "Pet House"), None)

    all_tasks = []
    generated_task_ids = set()

    def process_item(item, is_infra):
        instances = get_instances(state, int(item.data_id))
        
        max_count = 1
        if item.resource == ResourceType.BUILDER and item.count_by_th:
            max_count = item.count_by_th.get(current_infra["TH"], 1)
            
        while len(instances) < max_count:
            instances.append(0)
            
        if not instances:
            return

        timer = 0
        for category in ["buildings", "units", "heroes", "spells", "siege_machines", "pets", "traps"]:  # FIX: Add traps
            if item.data_id in state[category]:
                timer = state[category][item.data_id].get("timer", 0)
                break

        for instance_idx, start_lvl in enumerate(instances):
            prev_task_id = None
            
            for level_meta in item.levels:
                if level_meta.level <= start_lvl:
                    continue
                
                # FIX: Use max_infra for ceiling checks, not current_infra
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]:
                    break
                if level_meta.hero_hall_required and level_meta.hero_hall_required > max_infra["HeroHall"]:  # FIX: Use max_infra
                    break
                if level_meta.lab_required and level_meta.lab_required > max_infra["Lab"]:  # FIX: Use max_infra
                    break
                if level_meta.pet_house_required and level_meta.pet_house_required > max_infra["PetHouse"]:  # FIX: Use max_infra
                    break

                task_id = f"{item.data_id}_{level_meta.level}_{instance_idx}"
                deps = [prev_task_id] if prev_task_id else []
                
                # FIX: Add dependencies on infrastructure upgrades
                if not is_infra and item.resource == ResourceType.BUILDER:
                    if level_meta.hero_hall_required and hero_hall_id:
                        hh_dep = f"{hero_hall_id}_{level_meta.hero_hall_required}_0"
                        if hh_dep in generated_task_ids:
                            deps.append(hh_dep)
                            
                if not is_infra and item.resource == ResourceType.PET:
                    if level_meta.pet_house_required and pet_house_id:
                        ph_dep = f"{pet_house_id}_{level_meta.pet_house_required}_0"
                        if ph_dep in generated_task_ids:
                            deps.append(ph_dep)

                release_time = 0
                if timer > 0 and start_lvl > 0 and level_meta.level == start_lvl + 1 and instance_idx == 0:
                    release_time = timer

                all_tasks.append(Task(
                    id=task_id, duration=level_meta.duration_seconds, deps=deps,
                    resource=item.resource, release_time=release_time
                ))
                generated_task_ids.add(task_id)
                prev_task_id = task_id

    for item in infra_items:
        process_item(item, is_infra=True)
        
    for item in regular_items:
        process_item(item, is_infra=False)

    return all_tasks