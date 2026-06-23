"""
Logging utilities for Clash of Clans Upgrade Optimizer
"""

import logging
import sys
from typing import Optional
from pathlib import Path
from config import config

def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Setup a logger with consistent configuration"""
    logger = logging.getLogger(name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    else:
        logger.setLevel(getattr(logging, config.config.logging.level.upper()))
    
    # Avoid adding multiple handlers
    if not logger.handlers:
        logger.propagate = False
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # Console formatter
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        logger.addHandler(console_handler)
        
        # File handler if configured
        if config.config.logging.file:
            try:
                file_handler = logging.FileHandler(config.config.logging.file)
                file_handler.setLevel(logging.DEBUG)
                
                file_formatter = logging.Formatter(
                    config.config.logging.format
                )
                file_handler.setFormatter(file_formatter)
                
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Could not setup file handler: {e}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return setup_logger(name)

class PipelineLogger:
    """Specialized logger for pipeline operations"""
    
    def __init__(self, name: str = "pipeline"):
        self.logger = setup_logger(name)
    
    def log_pipeline_start(self, export_file: str, data_dir: str):
        """Log pipeline start"""
        self.logger.info(f"Starting pipeline with export: {export_file}")
        self.logger.info(f"Using data directory: {data_dir}")
    
    def log_metadata_loaded(self, count: int):
        """Log metadata loading completion"""
        self.logger.info(f"Loaded metadata for {count} items")
    
    def log_tasks_generated(self, count: int):
        """Log task generation completion"""
        self.logger.info(f"Generated {count} tasks")
    
    def log_solver_start(self, time_limit: int):
        """Log solver start"""
        self.logger.info(f"Starting solver with {time_limit}s time limit")
    
    def log_solver_complete(self, schedule_count: int, makespan: float):
        """Log solver completion"""
        self.logger.info(f"Solver complete: {schedule_count} tasks scheduled, makespan: {makespan:.1f} days")
    
    def log_pipeline_complete(self, output_file: str):
        """Log pipeline completion"""
        self.logger.info(f"Pipeline complete, output saved to: {output_file}")
    
    def log_error(self, operation: str, error: Exception):
        """Log error with context"""
        self.logger.error(f"Error in {operation}: {type(error).__name__}: {error}")

class ValidationLogger:
    """Specialized logger for validation operations"""
    
    def __init__(self, name: str = "validation"):
        self.logger = setup_logger(name)
    
    def log_validation_start(self, schedule_file: str):
        """Log validation start"""
        self.logger.info(f"Validating schedule: {schedule_file}")
    
    def log_dependency_check(self, task_id: str, dependencies: list):
        """Log dependency check"""
        if dependencies:
            self.logger.debug(f"Task {task_id} has dependencies: {dependencies}")
        else:
            self.logger.debug(f"Task {task_id} has no dependencies")
    
    def log_schedule_valid(self):
        """Log successful validation"""
        self.logger.info("Schedule validation passed - no conflicts found")
    
    def log_conflict_found(self, task_id: str, conflict: str):
        """Log schedule conflict"""
        self.logger.error(f"Schedule conflict found in task {task_id}: {conflict}")
    
    def log_error(self, operation: str, error: Exception):
        """Log error with context"""
        self.logger.error(f"Error in {operation}: {type(error).__name__}: {error}")
class AnalysisLogger:
    """Specialized logger for analysis operations"""
    
    def __init__(self, name: str = "analysis"):
        self.logger = setup_logger(name)
    
    def log_analysis_start(self, export_file: str):
        """Log analysis start"""
        self.logger.info(f"Starting analysis for: {export_file}")
    
    def log_workload_summary(self, total_hours: dict, resource_hours: dict):
        """Log workload summary"""
        self.logger.info("Workload Analysis Summary:")
        for resource, hours in resource_hours.items():
            self.logger.info(f"  {resource}: {hours} hours")
        self.logger.info(f"Total workload: {total_hours} hours")
    
    def log_theoretical_bounds(self, min_makespan: float, resource_constraints: dict):
        """Log theoretical bounds"""
        self.logger.info("Theoretical Bounds:")
        self.logger.info(f"  Minimum makespan: {min_makespan:.1f} days")
        for resource, count in resource_constraints.items():
            self.logger.info(f"  {resource}: {count} machines")

# Convenience instances
pipeline_logger = PipelineLogger()
validation_logger = ValidationLogger()
analysis_logger = AnalysisLogger()