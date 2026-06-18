# optimizer/task_generator.py
import json
from pathlib import Path
from typing import Any
from models import Task, NormalizedTaskMetadata, ResourceType

def parse_export_state(export_data: dict) -> dict[str, Any]:
    state: dict[str, Any] = {
        "buildings": {}, "units": {}, "heroes": {}, 
        "spells": {}, "siege_machines": {}, "pets": {}, "traps": {}
    }
    
    def process_list(key: str, items: list[dict]) -> None:
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
    process_list("traps", export_data.get("traps", []) + export_data.get("traps2", []))
    return state

def get_infra_levels(state: dict[str, Any], metadata: list[NormalizedTaskMetadata]) -> dict[str, int]:
    infra: dict[str, int] = {
        "TH": 1, "Lab": 1, "PetHouse": 1, "HeroHall": 1, "Blacksmith": 1, 
        "DSF": 1, "SF": 1, "Workshop": 1, "Barracks": 1, "DarkBarracks": 1
    }
    name_map = {
        "Town Hall": "TH", "Laboratory": "Lab", "Pet House": "PetHouse", 
        "Hero Hall": "HeroHall", "Blacksmith": "Blacksmith", 
        "Dark Spell Factory": "DSF", "Spell Factory": "SF", "Workshop": "Workshop",
        "Barracks": "Barracks", "Dark Barracks": "DarkBarracks"
    }
    for task in metadata:
        if task.name in name_map and task.resource == ResourceType.BUILDER:
            key = name_map[task.name]
            data_id_int = int(task.data_id)
            if data_id_int in state["buildings"]:
                levels_dict = state["buildings"][data_id_int]["levels"]
                if levels_dict: 
                    infra[key] = max(levels_dict.keys())
    return infra

def get_max_possible_infra(state: dict[str, Any], metadata: list[NormalizedTaskMetadata], current_infra: dict[str, int]) -> dict[str, int]:
    max_infra = current_infra.copy()
    infra_names = {
        "Laboratory": "Lab", "Pet House": "PetHouse", "Hero Hall": "HeroHall", 
        "Blacksmith": "Blacksmith", "Dark Spell Factory": "DSF", "Spell Factory": "SF", 
        "Workshop": "Workshop", "Barracks": "Barracks", "Dark Barracks": "DarkBarracks"
    }
    
    for task in metadata:
        if task.name in infra_names:
            key = infra_names[task.name]
            instances: list[int] = []
            data_id_int = int(task.data_id)
            if data_id_int in state["buildings"]:
                for lvl, cnt in state["buildings"][data_id_int]["levels"].items():
                    instances.extend([lvl] * cnt)
            current_lvl = max(instances) if instances else 0
            
            max_lvl = current_lvl
            for level_meta in task.levels:
                if level_meta.level <= current_lvl: 
                    continue
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]: 
                    break
                max_lvl = level_meta.level
            max_infra[key] = max_lvl
    return max_infra

def get_instances(state: dict[str, Any], data_id: int) -> list[int]:
    for category in ["buildings", "units", "heroes", "spells", "siege_machines", "pets", "traps"]:
        if data_id in state[category]:
            levels_dict = state[category][data_id]["levels"]
            instances: list[int] = []
            for lvl, cnt in levels_dict.items(): 
                instances.extend([lvl] * cnt)
            return instances
    return []

def generate_tasks(export_data: dict, metadata: list[NormalizedTaskMetadata]) -> list[Task]:
    state = parse_export_state(export_data)
    current_infra = get_infra_levels(state, metadata)
    max_infra = get_max_possible_infra(state, metadata, current_infra)
    
    infra_names_list = [
        "Laboratory", "Pet House", "Hero Hall", "Blacksmith", 
        "Dark Spell Factory", "Spell Factory", "Workshop", "Barracks", "Dark Barracks"
    ]
    infra_names_set = set(infra_names_list)
    
    infra_items = [m for m in metadata if m.name in infra_names_set]
    regular_items = [m for m in metadata if m.name not in infra_names_set and m.name != "Town Hall"]

    all_tasks: list[Task] = []
    generated_task_ids: set[str] = set()
    infra_task_map: dict[tuple[int, int], str] = {} 

    infra_id_map: dict[str, int] = {}
    for m in metadata:
        name = m.name
        mid = int(m.data_id)
        if name == "Laboratory": infra_id_map["Lab"] = mid
        elif name == "Pet House": infra_id_map["PetHouse"] = mid
        elif name == "Hero Hall": infra_id_map["HeroHall"] = mid
        elif name == "Dark Spell Factory": infra_id_map["DSF"] = mid
        elif name == "Spell Factory": infra_id_map["SF"] = mid
        elif name == "Workshop": infra_id_map["Workshop"] = mid
        elif name == "Barracks": infra_id_map["Barracks"] = mid
        elif name == "Dark Barracks": infra_id_map["DarkBarracks"] = mid

    # --- PASS 1: Generate Infrastructure Tasks ---
    for item in infra_items:
        instances = get_instances(state, int(item.data_id))
        if not instances: 
            instances = [0]
        
        for instance_idx, start_lvl in enumerate(instances):
            prev_task_id = None
            for level_meta in item.levels:
                if level_meta.level <= start_lvl: continue
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]: break

                task_id = f"{item.data_id}_{level_meta.level}_{instance_idx}"
                deps = [prev_task_id] if prev_task_id else []
                
                all_tasks.append(Task(id=task_id, duration=level_meta.duration_seconds, deps=deps, resource=item.resource))
                generated_task_ids.add(task_id)
                infra_task_map[(int(item.data_id), level_meta.level)] = task_id
                prev_task_id = task_id

    # --- PASS 2: Generate Regular Tasks ---
    for item in regular_items:
        instances = get_instances(state, int(item.data_id))
        max_count = 1
        if item.resource == ResourceType.BUILDER and item.count_by_th:
            max_count = item.count_by_th.get(current_infra["TH"], 1)
        while len(instances) < max_count: 
            instances.append(0)
        if not instances: 
            continue

        timer: int = 0 
        data_id_int = int(item.data_id)
        for category in ["buildings", "units", "heroes", "spells", "siege_machines", "pets", "traps"]:
            if data_id_int in state[category]:
                timer = state[category][data_id_int].get("timer", 0)
                break

        for instance_idx, start_lvl in enumerate(instances):
            prev_task_id = None
            for level_meta in item.levels:
                if level_meta.level <= start_lvl: continue
                
                # Ceilings
                if level_meta.town_hall_required and level_meta.town_hall_required > current_infra["TH"]: break
                if level_meta.hero_hall_required and level_meta.hero_hall_required > max_infra["HeroHall"]: break
                if level_meta.lab_required and level_meta.lab_required > max_infra["Lab"]: break
                if level_meta.pet_house_required and level_meta.pet_house_required > max_infra["PetHouse"]: break
                if level_meta.dark_spell_factory_required and level_meta.dark_spell_factory_required > max_infra["DSF"]: break
                if level_meta.spell_factory_required and level_meta.spell_factory_required > max_infra["SF"]: break
                if level_meta.workshop_required and level_meta.workshop_required > max_infra["Workshop"]: break
                if level_meta.barracks_required and level_meta.barracks_required > max_infra["Barracks"]: break
                if level_meta.dark_barracks_required and level_meta.dark_barracks_required > max_infra["DarkBarracks"]: break

                task_id = f"{item.data_id}_{level_meta.level}_{instance_idx}"
                deps = [prev_task_id] if prev_task_id else []
                
                # --- DEPENDENCIES ---
                if level_meta.lab_required and level_meta.lab_required > current_infra["Lab"]:
                    dep_id = infra_task_map.get((infra_id_map.get("Lab", 0), level_meta.lab_required))
                    if dep_id: deps.append(dep_id)
                    
                if level_meta.pet_house_required and level_meta.pet_house_required > current_infra["PetHouse"]:
                    dep_id = infra_task_map.get((infra_id_map.get("PetHouse", 0), level_meta.pet_house_required))
                    if dep_id: deps.append(dep_id)

                if level_meta.dark_spell_factory_required and level_meta.dark_spell_factory_required > current_infra["DSF"]:
                    dep_id = infra_task_map.get((infra_id_map.get("DSF", 0), level_meta.dark_spell_factory_required))
                    if dep_id: deps.append(dep_id)

                if level_meta.spell_factory_required and level_meta.spell_factory_required > current_infra["SF"]:
                    dep_id = infra_task_map.get((infra_id_map.get("SF", 0), level_meta.spell_factory_required))
                    if dep_id: deps.append(dep_id)

                if level_meta.hero_hall_required and level_meta.hero_hall_required > current_infra["HeroHall"]:
                    dep_id = infra_task_map.get((infra_id_map.get("HeroHall", 0), level_meta.hero_hall_required))
                    if dep_id: deps.append(dep_id)

                if level_meta.workshop_required and level_meta.workshop_required > current_infra["Workshop"]:
                    dep_id = infra_task_map.get((infra_id_map.get("Workshop", 0), level_meta.workshop_required))
                    if dep_id: deps.append(dep_id)

                # Barracks Dependencies (Only for unlocking Level 1 of a new troop)
                # Barracks Dependencies (Required for ALL levels if the troop isn't unlocked yet)
                if level_meta.barracks_required and level_meta.barracks_required > current_infra["Barracks"]:
                    dep_id = infra_task_map.get((infra_id_map.get("Barracks", 0), level_meta.barracks_required))
                    if dep_id: deps.append(dep_id)
                    
                if level_meta.dark_barracks_required and level_meta.dark_barracks_required > current_infra["DarkBarracks"]:
                    dep_id = infra_task_map.get((infra_id_map.get("DarkBarracks", 0), level_meta.dark_barracks_required))
                    if dep_id: deps.append(dep_id)

                release_time = 0
                if timer > 0 and start_lvl > 0 and level_meta.level == start_lvl + 1 and instance_idx == 0:
                    release_time = timer

                all_tasks.append(Task(id=task_id, duration=level_meta.duration_seconds, deps=deps, resource=item.resource, release_time=release_time))
                generated_task_ids.add(task_id)
                prev_task_id = task_id

    return all_tasks