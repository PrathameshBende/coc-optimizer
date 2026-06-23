"""
Configuration management for Clash of Clans Upgrade Optimizer
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class MachineConfig:
    builder_count: int = 5
    lab_count: int = 1
    pet_count: int = 1

@dataclass
class PathConfig:
    data_dir: str = str(Path(__file__).parent / "clash-of-clans-data/data/home")
    schedule_file: str = "schedule.json"
    village_export_file: str = "village_export.json"
    completed_tasks_file: str = "completed_tasks.json"
    metadata_cache_file: str = "parsed_metadata.json"
    backup_dir: str = "backups"

@dataclass
class SolverConfig:
    time_limit_seconds: int = 180
    target_gap_percentage: float = 0.5
    enable_progress_callback: bool = True

@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file: Optional[str] = None

@dataclass
class Config:
    environment: Environment = Environment.DEVELOPMENT
    machine: MachineConfig = field(default_factory=MachineConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    solver: SolverConfig = field(default_factory=SolverConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Extension-specific settings
    extension_enabled: bool = True
    extension_refresh_interval: int = 5  # seconds
    extension_notifications: bool = True

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self._setup_logging()
    
    def _load_config(self) -> Config:
        """Load configuration from file, environment variables, and defaults"""
        config_data = {}
        
        # Load from file if it exists
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.warning(f"Could not load config file: {e}")
        
        # Override with environment variables
        env_overrides = self._get_env_overrides()
        config_data = self._merge_configs(config_data, env_overrides)
        
        # Create Config object
        return self._dict_to_config(config_data)
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Environment
        if env := os.getenv("COC_OPTIMIZER_ENV"):
            overrides["environment"] = env
        
        # Machine counts
        if builder_count := os.getenv("COC_BUILDER_COUNT"):
            overrides.setdefault("machine", {})["builder_count"] = int(builder_count)
        if lab_count := os.getenv("COC_LAB_COUNT"):
            overrides.setdefault("machine", {})["lab_count"] = int(lab_count)
        if pet_count := os.getenv("COC_PET_COUNT"):
            overrides.setdefault("machine", {})["pet_count"] = int(pet_count)
        
        # Paths
        if data_dir := os.getenv("COC_DATA_DIR"):
            overrides.setdefault("paths", {})["data_dir"] = data_dir
        if schedule_file := os.getenv("COC_SCHEDULE_FILE"):
            overrides.setdefault("paths", {})["schedule_file"] = schedule_file
        if village_file := os.getenv("COC_VILLAGE_FILE"):
            overrides.setdefault("paths", {})["village_export_file"] = village_file
        
        # Solver
        if time_limit := os.getenv("COC_SOLVER_TIME_LIMIT"):
            overrides.setdefault("solver", {})["time_limit_seconds"] = int(time_limit)
        if gap := os.getenv("COC_SOLVER_GAP"):
            overrides.setdefault("solver", {})["target_gap_percentage"] = float(gap)
        
        return overrides
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _dict_to_config(self, data: Dict[str, Any]) -> Config:
        """Convert dictionary to Config object"""
        config = Config()
        
        # Environment
        if "environment" in data:
            config.environment = Environment(data["environment"])
        
        # Machine config
        if "machine" in data:
            machine_data = data["machine"]
            config.machine.builder_count = machine_data.get("builder_count", 5)
            config.machine.lab_count = machine_data.get("lab_count", 1)
            config.machine.pet_count = machine_data.get("pet_count", 1)
        
        # Path config
        if "paths" in data:
            path_data = data["paths"]
            config.paths.data_dir = path_data.get("data_dir", "clash-of-clans-data/data/home")
            config.paths.schedule_file = path_data.get("schedule_file", "schedule.json")
            config.paths.village_export_file = path_data.get("village_export_file", "village_export.json")
            config.paths.completed_tasks_file = path_data.get("completed_tasks_file", "completed_tasks.json")
            config.paths.metadata_cache_file = path_data.get("metadata_cache_file", "parsed_metadata.json")
            config.paths.backup_dir = path_data.get("backup_dir", "backups")
        
        # Solver config
        if "solver" in data:
            solver_data = data["solver"]
            config.solver.time_limit_seconds = solver_data.get("time_limit_seconds", 180)
            config.solver.target_gap_percentage = solver_data.get("target_gap_percentage", 0.5)
            config.solver.enable_progress_callback = solver_data.get("enable_progress_callback", True)
        
        # Logging config
        if "logging" in data:
            log_data = data["logging"]
            config.logging.level = log_data.get("level", "INFO")
            config.logging.format = log_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            config.logging.file = log_data.get("file")
        
        # Extension config
        config.extension_enabled = data.get("extension_enabled", True)
        config.extension_refresh_interval = data.get("extension_refresh_interval", 5)
        config.extension_notifications = data.get("extension_notifications", True)
        
        return config
    
    def _setup_logging(self):
        """Setup logging configuration"""
        level = getattr(logging, self.config.logging.level.upper())
        
        # Configure root logger
        logging.basicConfig(
            level=level,
            format=self.config.logging.format,
            filename=self.config.logging.file
        )
        
        # Create logger for this module
        self.logger = logging.getLogger(__name__)
    
    def save_config(self):
        """Save current configuration to file"""
        config_dict = {
            "environment": self.config.environment.value,
            "machine": {
                "builder_count": self.config.machine.builder_count,
                "lab_count": self.config.machine.lab_count,
                "pet_count": self.config.machine.pet_count
            },
            "paths": {
                "data_dir": self.config.paths.data_dir,
                "schedule_file": self.config.paths.schedule_file,
                "village_export_file": self.config.paths.village_export_file,
                "completed_tasks_file": self.config.paths.completed_tasks_file,
                "metadata_cache_file": self.config.paths.metadata_cache_file,
                "backup_dir": self.config.paths.backup_dir
            },
            "solver": {
                "time_limit_seconds": self.config.solver.time_limit_seconds,
                "target_gap_percentage": self.config.solver.target_gap_percentage,
                "enable_progress_callback": self.config.solver.enable_progress_callback
            },
            "logging": {
                "level": self.config.logging.level,
                "format": self.config.logging.format,
                "file": self.config.logging.file
            },
            "extension_enabled": self.config.extension_enabled,
            "extension_refresh_interval": self.config.extension_refresh_interval,
            "extension_notifications": self.config.extension_notifications
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except IOError as e:
            self.logger.error(f"Could not save config file: {e}")
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Get absolute path for a relative path, using config as base"""
        base_path = Path(__file__).parent.parent
        return base_path / relative_path
    
    def validate_config(self) -> bool:
        """Validate configuration and return True if valid"""
        try:
            # Check if required paths exist
            if self.config.paths.data_dir:
                data_path = self.get_absolute_path(self.config.paths.data_dir)
                if not data_path.exists():
                    self.logger.warning(f"Data directory does not exist: {data_path}")
            
            # Validate machine counts
            if self.config.machine.builder_count < 1:
                raise ValueError("Builder count must be at least 1")
            if self.config.machine.lab_count < 1:
                raise ValueError("Lab count must be at least 1")
            if self.config.machine.pet_count < 1:
                raise ValueError("Pet count must be at least 1")
            
            # Validate solver settings
            if self.config.solver.time_limit_seconds < 1:
                raise ValueError("Time limit must be at least 1 second")
            if not 0 <= self.config.solver.target_gap_percentage <= 100:
                raise ValueError("Gap percentage must be between 0 and 100")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

# Global configuration instance
config = ConfigManager()