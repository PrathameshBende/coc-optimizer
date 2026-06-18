# optimizer/run_pipeline.py
import json
import sys
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

def run_pipeline(export_path: str, data_dir: str):
    print(f"📂 Loading metadata...")
    metadata = parse_all_metadata(Path(data_dir))
    name_map = {int(item.data_id): item.name for item in metadata}
    
    print(f"📜 Loading village export...")
    with open(export_path, "r", encoding="utf-8") as f:
        export_data = json.load(f)
        
    print(f"⚙️  Generating unified task graph...")
    all_tasks = generate_tasks(export_data, metadata)
    print(f"✅ Generated {len(all_tasks)} tasks (Builders: {sum(1 for t in all_tasks if t.resource == ResourceType.BUILDER)}, Lab: {sum(1 for t in all_tasks if t.resource == ResourceType.LAB)}, Pets: {sum(1 for t in all_tasks if t.resource == ResourceType.PET)})")
    
    print(f"\n Running Unified CP-SAT Solver...")
    try:
        final_schedules = solve_exact(MACHINE_COUNTS, all_tasks, time_limit_seconds=180)
        makespan = max(s.end_time for s in final_schedules) if final_schedules else 0
        print(f"   ✅ Global Makespan: {makespan} hours ({makespan/24:.1f} days)")
    except Exception as e:
        print(f"   ❌ Failed to optimize: {e}")
        return

    print("\n" + "="*60)
    print(" FINAL OPTIMAL SCHEDULE")
    print("="*60)
    
    machine_tasks = defaultdict(list)
    for s in final_schedules:
        task = next((t for t in all_tasks if t.id == s.task_id), None)
        if task:
            machine_id_str = f"{task.resource.value} {s.machine_id}"
            machine_tasks[machine_id_str].append(s)

    for m_id in sorted(machine_tasks.keys()):
        print(f"\n⚙️ {m_id}")
        tasks = sorted(machine_tasks[m_id], key=lambda x: x.start_time)
        for ts in tasks:
            parts = ts.task_id.split('_')
            try:
                data_id_int = int(parts[0])
                friendly_name = name_map.get(data_id_int, "Unknown Building")
            except ValueError:
                friendly_name = "Unknown Building"
            print(f"  {ts.start_time//3600:4}h -> {ts.end_time//3600:4}h : {friendly_name} (Level {parts[1]})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <path_to_export.json> [path_to_data_dir]")
        sys.exit(1)
    export_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/zorro/Projects/optimizer/clash-of-clans-data/data/home"
    run_pipeline(export_path, data_dir)