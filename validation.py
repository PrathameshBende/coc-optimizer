"""
Data validation utilities for Clash of Clans Upgrade Optimizer
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from models import ResourceType

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class DataValidator:
    """Validates various data formats and structures"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_village_export(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate village export JSON structure"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check required top-level fields
        required_fields = ['buildings', 'heroes', 'spells']
        for field in required_fields:
            if field not in data:
                result.errors.append(f"Missing required field: {field}")
                result.is_valid = False
        
        # Validate each array type
        array_fields = [
            'buildings', 'buildings2', 'heroes', 'heroes2',
            'units', 'units2', 'siege_machines', 'spells',
            'pets', 'equipment', 'helpers'
        ]
        
        for field in array_fields:
            if field in data and not isinstance(data[field], list):
                result.errors.append(f"Field {field} must be an array")
                result.is_valid = False
            elif field in data:
                for i, item in enumerate(data[field]):
                    item_errors = self._validate_village_item(field, item, i)
                    result.errors.extend(item_errors)
                    if item_errors:
                        result.is_valid = False
        
        return result
    
    def _validate_village_item(self, array_type: str, item: Dict[str, Any], index: int) -> List[str]:
        """Validate individual village item"""
        errors = []
        
        if not isinstance(item, dict):
            errors.append(f"{array_type}[{index}] must be an object")
            return errors
        
        required_fields = ['data']
        for field in required_fields:
            if field not in item:
                errors.append(f"{array_type}[{index}] missing required field: {field}")
        
        if 'data' in item and not isinstance(item['data'], (int, str)):
            errors.append(f"{array_type}[{index}] data field must be number or string")
        
        if 'lvl' in item and not isinstance(item['lvl'], int):
            errors.append(f"{array_type}[{index}] lvl field must be integer")
        
        if 'cnt' in item and not isinstance(item['cnt'], int):
            errors.append(f"{array_type}[{index}] cnt field must be integer")
        
        return errors
    
    def validate_metadata(self, metadata: List[Dict[str, Any]]) -> ValidationResult:
        """Validate metadata structure"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        for i, item in enumerate(metadata):
            item_errors = self._validate_metadata_item(item, i)
            result.errors.extend(item_errors)
            if item_errors:
                result.is_valid = False
        
        return result
    
    def _validate_metadata_item(self, item: Dict[str, Any], index: int) -> List[str]:
        """Validate individual metadata item"""
        errors = []
        
        if not isinstance(item, dict):
            errors.append(f"Metadata[{index}] must be an object")
            return errors
        
        required_fields = ['data_id', 'name', 'resource']
        for field in required_fields:
            if field not in item:
                errors.append(f"Metadata[{index}] missing required field: {field}")
        
        if 'data_id' in item and not isinstance(item['data_id'], str):
            errors.append(f"Metadata[{index}] data_id must be string")
        
        if 'name' in item and not isinstance(item['name'], str):
            errors.append(f"Metadata[{index}] name must be string")
        
        if 'resource' in item:
            try:
                ResourceType(item['resource'])
            except ValueError:
                errors.append(f"Metadata[{index}] invalid resource type: {item['resource']}")
        
        if 'levels' in item:
            if not isinstance(item['levels'], list):
                errors.append(f"Metadata[{index}] levels must be an array")
            else:
                for j, level in enumerate(item['levels']):
                    level_errors = self._validate_level_item(level, index, j)
                    errors.extend(level_errors)
        
        return errors
    
    def _validate_level_item(self, level: Dict[str, Any], metadata_index: int, level_index: int) -> List[str]:
        """Validate individual level item"""
        errors = []
        
        if not isinstance(level, dict):
            errors.append(f"Metadata[{metadata_index}].levels[{level_index}] must be an object")
            return errors
        
        required_fields = ['level', 'duration_seconds']
        for field in required_fields:
            if field not in level:
                errors.append(f"Metadata[{metadata_index}].levels[{level_index}] missing required field: {field}")
        
        if 'level' in level and not isinstance(level['level'], int):
            errors.append(f"Metadata[{metadata_index}].levels[{level_index}] level must be integer")
        
        if 'duration_seconds' in level and not isinstance(level['duration_seconds'], int):
            errors.append(f"Metadata[{metadata_index}].levels[{level_index}] duration_seconds must be integer")
        
        # Validate optional required fields
        optional_required_fields = [
            'town_hall_required', 'hero_hall_required', 'lab_required',
            'pet_house_required', 'spell_factory_required', 'dark_spell_factory_required',
            'workshop_required', 'barracks_required', 'dark_barracks_required'
        ]
        
        for field in optional_required_fields:
            if field in level and not isinstance(level[field], int):
                errors.append(f"Metadata[{metadata_index}].levels[{level_index}] {field} must be integer")
        
        return errors
    
    def validate_schedule(self, schedule: Dict[str, Any]) -> ValidationResult:
        """Validate schedule structure"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check required top-level fields
        required_fields = ['resources', 'makespan_days']
        for field in required_fields:
            if field not in schedule:
                result.errors.append(f"Schedule missing required field: {field}")
                result.is_valid = False
        
        if 'resources' in schedule:
            if not isinstance(schedule['resources'], dict):
                result.errors.append("Schedule.resources must be an object")
                result.is_valid = False
            else:
                for resource_name, tasks in schedule['resources'].items():
                    if not isinstance(tasks, list):
                        result.errors.append(f"Schedule.resources.{resource_name} must be an array")
                        result.is_valid = False
                    else:
                        for i, task in enumerate(tasks):
                            task_errors = self._validate_schedule_task(task, resource_name, i)
                            result.errors.extend(task_errors)
                            if task_errors:
                                result.is_valid = False
        
        return result
    
    def _validate_schedule_task(self, task: Dict[str, Any], resource_name: str, index: int) -> List[str]:
        """Validate individual schedule task"""
        errors = []
        
        if not isinstance(task, dict):
            errors.append(f"Schedule.resources.{resource_name}[{index}] must be an object")
            return errors
        
        # Accept either start_time/end_time or start_hour/end_hour
        required_fields = ['task_id', 'name', 'level', 'duration_hours']
        has_start_time = 'start_time' in task or 'start_hour' in task
        has_end_time = 'end_time' in task or 'end_hour' in task
        
        for field in required_fields:
            if field not in task:
                errors.append(f"Schedule.resources.{resource_name}[{index}] missing required field: {field}")
        
        if not has_start_time:
            errors.append(f"Schedule.resources.{resource_name}[{index}] missing required field: start_time or start_hour")
        if not has_end_time:
            errors.append(f"Schedule.resources.{resource_name}[{index}] missing required field: end_time or end_hour")
        
        if 'task_id' in task and not isinstance(task['task_id'], str):
            errors.append(f"Schedule.resources.{resource_name}[{index}] task_id must be string")
        
        if 'name' in task and not isinstance(task['name'], str):
            errors.append(f"Schedule.resources.{resource_name}[{index}] name must be string")
        
        if 'level' in task and not isinstance(task['level'], int):
            errors.append(f"Schedule.resources.{resource_name}[{index}] level must be integer")
        
        if 'duration_hours' in task and not isinstance(task['duration_hours'], (int, float)):
            errors.append(f"Schedule.resources.{resource_name}[{index}] duration_hours must be number")
        
        if 'start_time' in task and not isinstance(task['start_time'], int):
            errors.append(f"Schedule.resources.{resource_name}[{index}] start_time must be integer")
        
        if 'end_time' in task and not isinstance(task['end_time'], int):
            errors.append(f"Schedule.resources.{resource_name}[{index}] end_time must be integer")
        
        if 'start_hour' in task and not isinstance(task['start_hour'], (int, float)):
            errors.append(f"Schedule.resources.{resource_name}[{index}] start_hour must be number")
        
        if 'end_hour' in task and not isinstance(task['end_hour'], (int, float)):
            errors.append(f"Schedule.resources.{resource_name}[{index}] end_hour must be number")
        
        return errors

class FileValidator:
    """Validates file operations and paths"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_file_exists(self, file_path: Union[str, Path], description: str = "File") -> bool:
        """Check if file exists"""
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"{description} not found: {path}")
            return False
        return True
    
    def validate_file_readable(self, file_path: Union[str, Path], description: str = "File") -> bool:
        """Check if file is readable"""
        path = Path(file_path)
        if not path.exists():
            self.logger.error(f"{description} not found: {path}")
            return False
        
        if not os.access(path, os.R_OK):
            self.logger.error(f"{description} not readable: {path}")
            return False
        
        return True
    
    def validate_json_file(self, file_path: Union[str, Path], description: str = "JSON file") -> Optional[Dict[str, Any]]:
        """Validate and parse JSON file"""
        if not self.validate_file_readable(file_path, description):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {description}: {e}")
            return None
        except IOError as e:
            self.logger.error(f"Error reading {description}: {e}")
            return None

class DependencyValidator:
    """Validates dependency relationships"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_task_dependencies(self, tasks: List[Dict[str, Any]]) -> ValidationResult:
        """Validate task dependency structure"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Create task ID to task mapping
        task_map = {task['task_id']: task for task in tasks}
        
        for task in tasks:
            task_id = task['task_id']
            dependencies = task.get('deps', [])
            
            # Check each dependency
            for dep_id in dependencies:
                if dep_id not in task_map:
                    result.errors.append(f"Task {task_id} references non-existent dependency: {dep_id}")
                    result.is_valid = False
                
                # Check for circular dependencies
                if self._has_circular_dependency(task_id, dep_id, task_map):
                    result.errors.append(f"Circular dependency detected involving tasks {task_id} and {dep_id}")
                    result.is_valid = False
        
        return result
    
    def _has_circular_dependency(self, task_id: str, dep_id: str, task_map: Dict[str, Dict[str, Any]], 
                                 visited: Optional[set] = None) -> bool:
        """Check for circular dependencies using DFS"""
        if visited is None:
            visited = set()
        
        if task_id in visited:
            return True
        
        if task_id not in task_map:
            return False
        
        visited.add(task_id)
        dependencies = task_map[task_id].get('deps', [])
        
        for dep in dependencies:
            if dep == dep_id:
                return True
            if self._has_circular_dependency(dep, dep_id, task_map, visited.copy()):
                return True
        
        return False

# Global validator instances
data_validator = DataValidator()
file_validator = FileValidator()
dependency_validator = DependencyValidator()