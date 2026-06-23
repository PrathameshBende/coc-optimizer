"""
Backup and restore functionality for Clash of Clans Upgrade Optimizer
"""

import json
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import os

class BackupManager:
    """Manages backup and restore operations for village data and configurations"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def create_backup(self, 
                     village_file: str, 
                     schedule_file: str, 
                     config_file: str = None,
                     description: str = None) -> str:
        """Create a backup of village data and configuration"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        try:
            backup_path.mkdir(exist_ok=True)
            
            # Create backup metadata
            metadata = {
                "timestamp": timestamp,
                "description": description or f"Backup created at {datetime.now()}",
                "files": {}
            }
            
            # Backup village file
            if Path(village_file).exists():
                village_backup = backup_path / "village_export.json"
                shutil.copy2(village_file, village_backup)
                metadata["files"]["village_export"] = str(village_backup)
                self.logger.info(f"Backed up village file: {village_file}")
            
            # Backup schedule file
            if Path(schedule_file).exists():
                schedule_backup = backup_path / "schedule.json"
                shutil.copy2(schedule_file, schedule_backup)
                metadata["files"]["schedule"] = str(schedule_backup)
                self.logger.info(f"Backed up schedule file: {schedule_file}")
            
            # Backup config file if specified
            if config_file and Path(config_file).exists():
                config_backup = backup_path / "config.json"
                shutil.copy2(config_file, config_backup)
                metadata["files"]["config"] = str(config_backup)
                self.logger.info(f"Backed up config file: {config_file}")
            
            # Save metadata
            metadata_file = backup_path / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self.logger.info(f"Backup created successfully: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            if backup_path.exists():
                shutil.rmtree(backup_path)
            raise
    
    def restore_backup(self, backup_path: str, target_dir: str = None) -> Dict[str, str]:
        """Restore files from a backup"""
        
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata not found in backup: {backup_path}")
        
        try:
            # Load metadata
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            restored_files = {}
            
            # Determine target directory
            if target_dir is None:
                target_dir = Path.cwd()
            else:
                target_dir = Path(target_dir)
                target_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore each file
            for file_name, file_path in metadata.get("files", {}).items():
                source_path = Path(file_path)
                if not source_path.exists():
                    self.logger.warning(f"File not found in backup: {file_path}")
                    continue
                
                target_file = target_dir / file_name
                shutil.copy2(source_path, target_file)
                restored_files[file_name] = str(target_file)
                self.logger.info(f"Restored: {source_path} -> {target_file}")
            
            self.logger.info(f"Backup restored successfully from: {backup_path}")
            return restored_files
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            raise
    
    def list_backups(self) -> list:
        """List all available backups"""
        backups = []
        
        for backup_dir in self.backup_dir.glob("backup_*"):
            if backup_dir.is_dir():
                metadata_file = backup_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        backups.append({
                            "path": str(backup_dir),
                            "timestamp": metadata.get("timestamp"),
                            "description": metadata.get("description", "No description")
                        })
                    except Exception as e:
                        self.logger.warning(f"Could not read backup metadata: {backup_dir} - {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def delete_backup(self, backup_path: str) -> bool:
        """Delete a backup"""
        
        backup_path = Path(backup_path)
        if not backup_path.exists():
            self.logger.warning(f"Backup not found: {backup_path}")
            return False
        
        try:
            shutil.rmtree(backup_path)
            self.logger.info(f"Backup deleted: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {e}")
            return False
    
    def get_backup_info(self, backup_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific backup"""
        
        backup_path = Path(backup_path)
        if not backup_path.exists():
            return None
        
        metadata_file = backup_path / "metadata.json"
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Add file listing
            files = []
            for file_name, file_path in metadata.get("files", {}).items():
                if Path(file_path).exists():
                    stat = Path(file_path).stat()
                    files.append({
                        "name": file_name,
                        "path": file_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            metadata["files"] = files
            return metadata
            
        except Exception as e:
            self.logger.error(f"Could not read backup info: {e}")
            return None

class AutoBackup:
    """Automatic backup functionality"""
    
    def __init__(self, backup_manager: BackupManager, config_file: str = "config.json"):
        self.backup_manager = backup_manager
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
    
    def backup_before_pipeline(self, village_file: str, schedule_file: str) -> str:
        """Create automatic backup before running pipeline"""
        
        description = "Auto-backup before pipeline execution"
        
        try:
            backup_path = self.backup_manager.create_backup(
                village_file=village_file,
                schedule_file=schedule_file,
                config_file=str(self.config_file),
                description=description
            )
            
            self.logger.info(f"Auto-backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create auto-backup: {e}")
            return None
    
    def restore_after_failure(self, backup_path: str, target_dir: str = None) -> Dict[str, str]:
        """Restore backup after pipeline failure"""
        
        try:
            restored_files = self.backup_manager.restore_backup(backup_path, target_dir)
            self.logger.info(f"Restored files from backup: {backup_path}")
            return restored_files
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {e}")
            raise

# Global instances
backup_manager = BackupManager()
auto_backup = AutoBackup(backup_manager)