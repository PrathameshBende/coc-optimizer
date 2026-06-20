# optimizer/run_pipeline.py
import json
import sys
import os
from pathlib import Path
from collections import defaultdict
from parsers import parse_all_metadata
from task_generator import generate_tasks
from exact_scheduler import solve_exact
from models import ResourceType, Task, TaskSchedule

MACHINE_COUNTS = {
    ResourceType.BUILDER: 5,
    ResourceType.LAB: 1,
    ResourceType.PET: 1
}

def run_pipeline(export_path: str, data_dir: str, output_path: str = "schedule.json"):
    print(f" Loading metadata...")
    metadata = parse_all_metadata(Path(data_dir))
    name_map = {int(item.data_id): item.name for item in metadata}
    
    print(f"📜 Loading village export...")
    with open(export_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)
        
    print(f"⚙️  Generating unified task graph...")
    all_tasks = generate_tasks(export_data, metadata)
    
    # Load completed tasks to remove them from the graph
    completed_ids = set()
    if os.path.exists("completed_tasks.json"):
        with open("completed_tasks.json", "r") as f:
            completed_ids = set(json.load(f))
            
    all_tasks = [t for t in all_tasks if t.id not in completed_ids]
    print(f"✅ Generated {len(all_tasks)} tasks (after removing {len(completed_ids)} completed).")
    
    print(f"\n🚀 Running Unified CP-SAT Solver...")
    try:
        final_schedules = solve_exact(MACHINE_COUNTS, all_tasks, time_limit_seconds=180)
        makespan_seconds = max(s.end_time for s in final_schedules) if final_schedules else 0
        print(f"   ✅ Global Makespan: {makespan_seconds / 3600} hours ({makespan_seconds / 86400:.1f} days)")
    except Exception as e:
        print(f"   ❌ Failed to optimize: {e}")
        return

    # Build structured JSON for the UI
    machine_tasks = defaultdict(list)
    for s in final_schedules:
        task = next((t for t in all_tasks if t.id == s.task_id), None)
        if task:
            machine_id_str = f"{task.resource.value} {s.machine_id}"
            machine_tasks[machine_id_str].append(s)
    makespan_seconds = max(s.end_time for s in final_schedules) if final_schedules else 0

    schedule_data = {
        "makespan_hours": makespan_seconds / 3600,
        "makespan_days": makespan_seconds / 86400,
        "resources": {}
    }
    
    for m_id, tasks in machine_tasks.items():
        tasks_sorted = sorted(tasks, key=lambda x: x.start_time)
        resource_schedule = []
        for ts in tasks_sorted:
            parts = ts.task_id.split('_')
            try:
                data_id_int = int(parts[0])
                friendly_name = name_map.get(data_id_int, "Unknown Building")
            except ValueError:
                friendly_name = "Unknown Building"
                
            resource_schedule.append({
                "task_id": ts.task_id,
                "name": friendly_name,
                "level": int(parts[1]),
                "start_hour": ts.start_time,
                "end_hour": ts.end_time / 3600,
                "duration_hours": (ts.end_time - ts.start_time) / 3600
            })
        schedule_data["resources"][m_id] = resource_schedule
        
    with open(output_path, "w") as f:
        json.dump(schedule_data, f, indent=2)
    print(f" Saved schedule to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <path_to_export.json> [path_to_data_dir]")
        sys.exit(1)
    export_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/zorro/Projects/optimizer/clash-of-clans-data/data/home"
    run_pipeline(export_path, data_dir)