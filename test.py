"""
Integration test script for the optimizer
Runs the full pipeline on the default village_export.json using the new configuration,
backup system, validation, and logs results.
"""

import sys
import os
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from run_pipeline import run_pipeline
from backup import auto_backup
from logging_utils import setup_logger


def main():
    village_path = str(project_root / "village_export.json")
    data_dir = str(project_root / "clash-of-clans-data" / "data" / "home")
    schedule_path = str(project_root / "schedule.json")

    if not Path(village_path).is_file():
        print(f"Village export not found: {village_path}")
        sys.exit(1)
    if not Path(data_dir).is_dir():
        print(f"Data directory not found: {data_dir}")
        sys.exit(1)

    # Create an auto-backup before pipeline
    try:
        backup_path = auto_backup.backup_before_pipeline(village_path, schedule_path)
        print(f"Backup created at {backup_path}")
    except Exception as e:
        print(f"Failed to create backup: {e}")
        sys.exit(1)

    # Run the pipeline
    try:
        print("Running pipeline...")
        result = run_pipeline(village_path, data_dir, schedule_path)
        print("Pipeline completed. Schedule saved to:", schedule_path)
    except Exception as e:
        print("Pipeline failed:", e)
        print("Restoring from backup...")
        auto_backup.restore_after_failure(backup_path, str(project_root))
        sys.exit(1)

    # Check the schedule output
    with open(schedule_path) as f:
        schedule_data = json.load(f)

    total_tasks = sum(len(tasks) for tasks in schedule_data.get("resources", {}).values())
    makespan = schedule_data.get("makespan_days", 0)

    print(f"\nSchedule summary:")
    print(f"  Total tasks scheduled: {total_tasks}")
    print(f"  Makespan: {makespan:.1f} days")

    if total_tasks == 0:
        print("ERROR: 0 tasks were scheduled — pipeline produced no results!")
        sys.exit(1)

    print("Test completed successfully.")


if __name__ == "__main__":
    setup_logger("test")
    main()
