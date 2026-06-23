"""
Caching system for Clash of Clans Upgrade Optimizer
"""

import json
import pickle
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import os

class CacheManager:
    """Manages caching of expensive operations"""
    
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def get_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = f"{args}_{kwargs}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cache_path(self, cache_type: str, key: str) -> Path:
        """Get file path for cache entry"""
        return self.cache_dir / f"{cache_type}_{key}.cache"
    
    def set_cache(self, cache_type: str, key: str, data: Any, ttl_hours: int = 24):
        """Set cached data with TTL"""
        cache_path = self.get_cache_path(cache_type, key)
        
        try:
            cache_entry = {
                'data': data,
                'created_at': datetime.now().isoformat(),
                'ttl_hours': ttl_hours
            }
            
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_entry, f)
            
            self.logger.debug(f"Cache set: {cache_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to set cache: {e}")
    
    def get_cache(self, cache_type: str, key: str) -> Optional[Any]:
        """Get cached data if valid and not expired"""
        cache_path = self.get_cache_path(cache_type, key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                cache_entry = pickle.load(f)
            
            # Check if expired
            created_at = datetime.fromisoformat(cache_entry['created_at'])
            ttl_hours = cache_entry['ttl_hours']
            
            if datetime.now() - created_at > timedelta(hours=ttl_hours):
                self.logger.debug(f"Cache expired: {cache_path}")
                cache_path.unlink()
                return None
            
            self.logger.debug(f"Cache hit: {cache_path}")
            return cache_entry['data']
            
        except Exception as e:
            self.logger.warning(f"Failed to get cache: {e}")
            if cache_path.exists():
                cache_path.unlink()
            return None
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache entries"""
        if cache_type:
            pattern = f"{cache_type}_*.cache"
            for cache_file in self.cache_dir.glob(pattern):
                cache_file.unlink()
                self.logger.debug(f"Cleared cache: {cache_file}")
        else:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()
            self.logger.debug("Cleared all cache")
    
    def cleanup_expired(self):
        """Remove expired cache files"""
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    cache_entry = pickle.load(f)
                
                created_at = datetime.fromisoformat(cache_entry['created_at'])
                ttl_hours = cache_entry['ttl_hours']
                
                if datetime.now() - created_at > timedelta(hours=ttl_hours):
                    cache_file.unlink()
                    self.logger.debug(f"Removed expired cache: {cache_file}")
                    
            except Exception as e:
                self.logger.warning(f"Failed to cleanup cache {cache_file}: {e}")
                cache_file.unlink()

class MetadataCache:
    """Caches parsed metadata"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def get_metadata(self, data_dir: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached metadata if available"""
        # Generate cache key based on data directory contents
        key = self._generate_metadata_key(data_dir)
        return self.cache_manager.get_cache('metadata', key)
    
    def set_metadata(self, data_dir: str, metadata: List[Dict[str, Any]]):
        """Cache parsed metadata"""
        key = self._generate_metadata_key(data_dir)
        self.cache_manager.set_cache('metadata', key, metadata, ttl_hours=168)  # 1 week
    
    def _generate_metadata_key(self, data_dir: str) -> str:
        """Generate cache key based on data directory state"""
        key_data = []
        data_path = Path(data_dir)
        
        if data_path.exists():
            # Use modification times of all JSON files (recursive)
            json_files = sorted(data_path.rglob("*.json"))
            
            for json_file in json_files:
                stat = json_file.stat()
                key_data.append(f"{json_file.name}:{stat.st_mtime}")
        
        return hashlib.md5("|".join(key_data).encode()).hexdigest()

class TaskCache:
    """Caches generated tasks"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def get_tasks(self, village_hash: str, metadata_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached tasks if available"""
        key = f"{village_hash}_{metadata_hash}"
        return self.cache_manager.get_cache('tasks', key)
    
    def set_tasks(self, village_hash: str, metadata_hash: str, tasks: List[Dict[str, Any]]):
        """Cache generated tasks"""
        key = f"{village_hash}_{metadata_hash}"
        self.cache_manager.set_cache('tasks', key, tasks, ttl_hours=24)  # 1 day
    
    def generate_village_hash(self, village_data: Dict[str, Any]) -> str:
        """Generate hash for village data"""
        return hashlib.md5(json.dumps(village_data, sort_keys=True).encode()).hexdigest()

class ScheduleCache:
    """Caches generated schedules"""
    
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
    
    def get_schedule(self, tasks_hash: str, machine_config_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached schedule if available"""
        key = f"{tasks_hash}_{machine_config_hash}"
        return self.cache_manager.get_cache('schedule', key)
    
    def set_schedule(self, tasks_hash: str, machine_config_hash: str, schedule: Dict[str, Any]):
        """Cache generated schedule"""
        key = f"{tasks_hash}_{machine_config_hash}"
        self.cache_manager.set_cache('schedule', key, schedule, ttl_hours=168)  # 1 week
    
    def generate_machine_config_hash(self, machine_counts: Dict[str, int]) -> str:
        """Generate hash for machine configuration"""
        return hashlib.md5(json.dumps(machine_counts, sort_keys=True).encode()).hexdigest()

class CacheDecorator:
    """Decorator for caching function results"""
    
    def __init__(self, cache_manager: CacheManager, cache_type: str, ttl_hours: int = 24):
        self.cache_manager = cache_manager
        self.cache_type = cache_type
        self.ttl_hours = ttl_hours
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = self.cache_manager.get_cache_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_result = self.cache_manager.get_cache(self.cache_type, key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            self.cache_manager.set_cache(self.cache_type, key, result, self.ttl_hours)
            return result
        
        return wrapper

# Global cache instances
cache_manager = CacheManager()
metadata_cache = MetadataCache(cache_manager)
task_cache = TaskCache(cache_manager)
schedule_cache = ScheduleCache(cache_manager)

# Convenience decorators
cache_metadata = CacheDecorator(cache_manager, 'metadata', 168)  # 1 week
cache_tasks = CacheDecorator(cache_manager, 'tasks', 24)  # 1 day
cache_schedule = CacheDecorator(cache_manager, 'schedule', 168)  # 1 week