# optimizer/run_pipeline.py
import json
import sys
import os
import logging
import hashlib
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any
from parsers import parse_all_metadata
from task_generator import generate_tasks
from exact_scheduler import solve_exact
from models import ResourceType, Task, TaskSchedule
from config import config
from logging_utils import pipeline_logger
from validation import data_validator, file_validator
from cache import metadata_cache, task_cache, schedule_cache

# Use machine counts from config
MACHINE_COUNTS = {
    ResourceType.BUILDER: config.config.machine.builder_count,
    ResourceType.LAB: config.config.machine.lab_count,
    ResourceType.PET: config.config.machine.pet_count
}

def run_pipeline(export_path: str, data_dir: str, output_path: str = None):
    """Run the complete optimization pipeline with logging and validation"""
    
    # Set default output path
    if output_path is None:
        output_path = config.config.paths.schedule_file
    
    try:
        # Validate inputs
        export_path_obj = Path(export_path)
        if not export_path_obj.exists():
            raise FileNotFoundError(f"Village export file not found: {export_path_obj}")
        
        data_dir_path = Path(data_dir)
        if not data_dir_path.exists():
            # Try relative to project root
            project_root = Path(__file__).parent
            data_dir_path = project_root / data_dir
            if not data_dir_path.exists():
                raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        # Log pipeline start
        pipeline_logger.log_pipeline_start(export_path, data_dir)
        
        # Load and validate metadata
        pipeline_logger.logger.info("Loading metadata...")
        
        # Try to get from cache first
        metadata = metadata_cache.get_metadata(data_dir)
        if metadata is None:
            metadata = parse_all_metadata(data_dir_path)
            metadata_cache.set_metadata(data_dir, metadata)
        
        pipeline_logger.log_metadata_loaded(len(metadata))
        
        # Load and validate village export
        pipeline_logger.logger.info("Loading village export...")
        export_data = file_validator.validate_json_file(export_path, "Village export")
        if export_data is None:
            raise ValueError("Invalid village export format")
        
        # Validate village data
        validation_result = data_validator.validate_village_export(export_data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid village export: {validation_result.errors}")
        
        # Generate tasks with caching
        pipeline_logger.logger.info("Generating unified task graph...")
        
        # Generate cache keys
        village_hash = task_cache.generate_village_hash(export_data)
        metadata_json = json.dumps([m.__dict__ for m in metadata], sort_keys=True, default=str)
        metadata_hash = hashlib.md5(metadata_json.encode()).hexdigest()
        
        # Try to get tasks from cache
        all_tasks = task_cache.get_tasks(village_hash, metadata_hash)
        if all_tasks is None:
            all_tasks = generate_tasks(export_data, metadata)
            task_cache.set_tasks(village_hash, metadata_hash, all_tasks)
        
        pipeline_logger.log_tasks_generated(len(all_tasks))
        
        # Load completed tasks
        completed_ids = set()
        completed_tasks_path = Path(config.config.paths.completed_tasks_file)
        if completed_tasks_path.exists():
            try:
                with open(completed_tasks_path, "r") as f:
                    completed_data = json.load(f)
                    if isinstance(completed_data, list):
                        completed_ids = set(completed_data)
            except Exception as e:
                pipeline_logger.logger.warning(f"Could not load completed tasks: {e}")
        
        # Filter out completed tasks
        all_tasks = [t for t in all_tasks if t.id not in completed_ids]
        pipeline_logger.logger.info(f"Generated {len(all_tasks)} tasks (after removing {len(completed_ids)} completed)")
        
        # Run solver
        pipeline_logger.logger.info("Running CP-SAT solver...")
        pipeline_logger.log_solver_start(config.config.solver.time_limit_seconds)
        
        try:
            final_schedules = solve_exact(
                MACHINE_COUNTS, 
                all_tasks, 
                time_limit_seconds=config.config.solver.time_limit_seconds
            )
            
            makespan_seconds = max(s.end_time for s in final_schedules) if final_schedules else 0
            pipeline_logger.log_solver_complete(len(final_schedules), makespan_seconds / 86400)
            
        except Exception as e:
            pipeline_logger.log_error("solver optimization", e)
            raise
        
        # Build structured JSON for the UI
        machine_tasks = defaultdict(list)
        for s in final_schedules:
            task = next((t for t in all_tasks if t.id == s.task_id), None)
            if task:
                machine_id_str = f"{task.resource.value} {s.machine_id}"
                machine_tasks[machine_id_str].append(s)
        
        makespan_seconds = max(s.end_time for s in final_schedules) if final_schedules else 0
        
        # Create schedule data
        name_map = {int(item.data_id): item.name for item in metadata}
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
        
        # Save schedule
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w") as f:
            json.dump(schedule_data, f, indent=2)
        
        pipeline_logger.log_pipeline_complete(output_path)
        
        # Validate output
        validation_result = data_validator.validate_schedule(schedule_data)
        if not validation_result.is_valid:
            pipeline_logger.logger.warning(f"Schedule validation warnings: {validation_result.warnings}")
            if validation_result.errors:
                raise ValueError(f"Schedule validation errors: {validation_result.errors}")
        
        return schedule_data
        
    except Exception as e:
        pipeline_logger.log_error("pipeline", e)
        raise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <path_to_export.json> [path_to_data_dir]")
        sys.exit(1)
    
    export_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else config.config.paths.data_dir
    
    print(f"Starting pipeline with:")
    print(f"  Export: {export_path}")
    print(f"  Data dir: {data_dir}")
    print(f"  Output: {config.config.paths.schedule_file}")
    print(f"  Config: {config.config_file}")
    
    try:
        result = run_pipeline(export_path, data_dir)
        print("Pipeline completed successfully!")
        print(f"Schedule saved to: {config.config.paths.schedule_file}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)