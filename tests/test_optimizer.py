"""
Unit tests for Clash of Clans Upgrade Optimizer
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Task, ResourceType, TaskSchedule, NormalizedLevel, NormalizedTaskMetadata
from validation import DataValidator, FileValidator, ValidationResult
from config import ConfigManager, Config
from cache import CacheManager, MetadataCache, TaskCache, CacheDecorator

class TestModels(unittest.TestCase):
    """Test data model classes"""
    
    def test_task_creation(self):
        """Test Task creation and validation"""
        task = Task(
            id="test_task_1",
            duration=3600,
            deps=["dep1", "dep2"],
            resource=ResourceType.BUILDER
        )
        
        self.assertEqual(task.id, "test_task_1")
        self.assertEqual(task.duration, 3600)
        self.assertEqual(task.deps, ["dep1", "dep2"])
        self.assertEqual(task.resource, ResourceType.BUILDER)
    
    def test_task_schedule_creation(self):
        """Test TaskSchedule creation"""
        schedule = TaskSchedule(
            task_id="test_task_1",
            machine_id=1,
            start_time=0,
            end_time=3600
        )
        
        self.assertEqual(schedule.task_id, "test_task_1")
        self.assertEqual(schedule.machine_id, 1)
        self.assertEqual(schedule.start_time, 0)
        self.assertEqual(schedule.end_time, 3600)
    
    def test_normalized_level_creation(self):
        """Test NormalizedLevel creation"""
        level = NormalizedLevel(
            level=5,
            duration_seconds=86400,
            town_hall_required=10
        )
        
        self.assertEqual(level.level, 5)
        self.assertEqual(level.duration_seconds, 86400)
        self.assertEqual(level.town_hall_required, 10)
        self.assertIsNone(level.lab_required)
    
    def test_normalized_task_metadata_creation(self):
        """Test NormalizedTaskMetadata creation"""
        metadata = NormalizedTaskMetadata(
            data_id="28000000",
            name="Test Building",
            resource=ResourceType.BUILDER
        )
        
        self.assertEqual(metadata.data_id, "28000000")
        self.assertEqual(metadata.name, "Test Building")
        self.assertEqual(metadata.resource, ResourceType.BUILDER)
        self.assertEqual(len(metadata.levels), 0)

class TestValidation(unittest.TestCase):
    """Test validation utilities"""
    
    def setUp(self):
        self.validator = DataValidator()
    
    def test_valid_village_export(self):
        """Test validation of valid village export"""
        valid_data = {
            'buildings': [
                {'data': 28000000, 'lvl': 1, 'cnt': 1}
            ],
            'heroes': [
                {'data': 29000000, 'lvl': 0}
            ],
            'spells': [
                {'data': 26000000, 'lvl': 0}
            ]
        }
        
        result = self.validator.validate_village_export(valid_data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_invalid_village_export(self):
        """Test validation of invalid village export"""
        invalid_data = {
            'buildings': "not an array",
            'heroes': [
                {'data': "invalid", 'lvl': "not a number"}
            ]
        }
        
        result = self.validator.validate_village_export(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)
    
    def test_metadata_validation(self):
        """Test metadata validation"""
        valid_metadata = [
            {
                'data_id': '28000000',
                'name': 'Town Hall',
                'resource': 'BUILDER',
                'levels': [
                    {
                        'level': 1,
                        'duration_seconds': 86400,
                        'town_hall_required': 1
                    }
                ]
            }
        ]
        
        result = self.validator.validate_metadata(valid_metadata)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)
    
    def test_file_validator(self):
        """Test file validation"""
        file_validator = FileValidator()
        
        # Test non-existent file
        self.assertFalse(file_validator.validate_file_exists("nonexistent.json"))
        
        # Test with temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'test': 'data'}, f)
            temp_file = f.name
        
        try:
            self.assertTrue(file_validator.validate_file_exists(temp_file))
            self.assertTrue(file_validator.validate_file_readable(temp_file))
            
            data = file_validator.validate_json_file(temp_file)
            self.assertIsNotNone(data)
            self.assertEqual(data['test'], 'data')
            
        finally:
            Path(temp_file).unlink()

class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def tearDown(self):
        # Clean up temp files
        for file in Path(self.temp_dir).glob("*"):
            file.unlink()
        Path(self.temp_dir).rmdir()
    
    def test_default_config(self):
        """Test default configuration"""
        config_manager = ConfigManager(str(self.config_file))
        config = config_manager.config
        
        self.assertEqual(config.machine.builder_count, 5)
        self.assertEqual(config.machine.lab_count, 1)
        self.assertEqual(config.machine.pet_count, 1)
        self.assertTrue(config.paths.data_dir.endswith("clash-of-clans-data/data/home"))
        self.assertEqual(config.solver.time_limit_seconds, 180)
    
    def test_config_override(self):
        """Test configuration override"""
        # Create test config file
        test_config = {
            "machine": {
                "builder_count": 10,
                "lab_count": 2
            },
            "solver": {
                "time_limit_seconds": 300
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(test_config, f)
        
        config_manager = ConfigManager(str(self.config_file))
        config = config_manager.config
        
        self.assertEqual(config.machine.builder_count, 10)
        self.assertEqual(config.machine.lab_count, 2)
        self.assertEqual(config.solver.time_limit_seconds, 300)
    
    def test_config_validation(self):
        """Test configuration validation"""
        config_manager = ConfigManager(str(self.config_file))
        
        # Valid config
        self.assertTrue(config_manager.validate_config())
        
        # Invalid config
        config_manager.config.machine.builder_count = 0
        self.assertFalse(config_manager.validate_config())
    
    def test_environment_variables(self):
        """Test environment variable override"""
        with patch.dict('os.environ', {
            'COC_BUILDER_COUNT': '8',
            'COC_LAB_COUNT': '3'
        }):
            config_manager = ConfigManager(str(self.config_file))
            config = config_manager.config
            
            self.assertEqual(config.machine.builder_count, 8)
            self.assertEqual(config.machine.lab_count, 3)

class TestCache(unittest.TestCase):
    """Test caching system"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(self.temp_dir)
    
    def tearDown(self):
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_cache_operations(self):
        """Test basic cache operations"""
        test_data = {'test': 'data', 'number': 42}
        
        # Set cache
        self.cache_manager.set_cache('test', 'key1', test_data)
        
        # Get cache
        retrieved_data = self.cache_manager.get_cache('test', 'key1')
        self.assertEqual(retrieved_data, test_data)
        
        # Test non-existent cache
        nonexistent = self.cache_manager.get_cache('test', 'nonexistent')
        self.assertIsNone(nonexistent)
    
    def test_cache_expiry(self):
        """Test cache expiry"""
        test_data = {'test': 'data'}
        
        # Set cache with zero TTL (immediately expired)
        self.cache_manager.set_cache('test', 'key1', test_data, ttl_hours=0)
        
        # Should be expired immediately
        retrieved_data = self.cache_manager.get_cache('test', 'key1')
        self.assertIsNone(retrieved_data)
    
    def test_metadata_cache(self):
        """Test metadata caching"""
        metadata_cache = MetadataCache(self.cache_manager)
        
        test_metadata = [
            {
                'data_id': '28000000',
                'name': 'Town Hall',
                'resource': 'BUILDER',
                'levels': []
            }
        ]
        
        # Set cache
        metadata_cache.set_metadata('test_dir', test_metadata)
        
        # Get cache
        retrieved = metadata_cache.get_metadata('test_dir')
        self.assertEqual(retrieved, test_metadata)
    
    def test_task_cache(self):
        """Test task caching"""
        task_cache = TaskCache(self.cache_manager)
        
        test_tasks = [
            {
                'task_id': 'task1',
                'duration': 3600,
                'deps': [],
                'resource': 'BUILDER'
            }
        ]
        
        village_hash = 'village123'
        metadata_hash = 'metadata456'
        
        # Set cache
        task_cache.set_tasks(village_hash, metadata_hash, test_tasks)
        
        # Get cache
        retrieved = task_cache.get_tasks(village_hash, metadata_hash)
        self.assertEqual(retrieved, test_tasks)
    
    def test_cache_decorator(self):
        """Test cache decorator"""
        @CacheDecorator(self.cache_manager, 'decorated_test', 1)
        def test_function(x, y):
            return x + y
        
        # First call should execute and cache
        result1 = test_function(1, 2)
        self.assertEqual(result1, 3)
        
        # Second call should use cache
        result2 = test_function(1, 2)
        self.assertEqual(result2, 3)
        
        # Different arguments should execute again
        result3 = test_function(2, 2)
        self.assertEqual(result3, 4)

class TestIntegration(unittest.TestCase):
    """Integration tests"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.cache_manager = CacheManager(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_pipeline_simulation(self):
        """Simulate a full pipeline run with caching"""
        # Create test configuration
        config_manager = ConfigManager(str(self.config_file))
        config = config_manager.config
        
        # Create test data
        test_village = {
            'buildings': [{'data': 28000000, 'lvl': 1, 'cnt': 1}],
            'heroes': [],
            'spells': []
        }
        
        test_metadata = [
            {
                'data_id': '28000000',
                'name': 'Town Hall',
                'resource': 'BUILDER',
                'levels': [
                    {
                        'level': 2,
                        'duration_seconds': 86400,
                        'town_hall_required': 1
                    }
                ]
            }
        ]
        
        # Test caching components
        metadata_cache = MetadataCache(self.cache_manager)
        task_cache = TaskCache(self.cache_manager)
        
        # Cache metadata
        metadata_cache.set_metadata('test_data', test_metadata)
        retrieved_metadata = metadata_cache.get_metadata('test_data')
        self.assertEqual(retrieved_metadata, test_metadata)
        
        # Cache tasks
        village_hash = task_cache.generate_village_hash(test_village)
        metadata_hash = 'metadata_hash'
        
        test_tasks = [
            {
                'task_id': 'task1',
                'duration': 86400,
                'deps': [],
                'resource': 'BUILDER'
            }
        ]
        
        task_cache.set_tasks(village_hash, metadata_hash, test_tasks)
        retrieved_tasks = task_cache.get_tasks(village_hash, metadata_hash)
        self.assertEqual(retrieved_tasks, test_tasks)
        
        # Test validation
        validator = DataValidator()
        village_result = validator.validate_village_export(test_village)
        self.assertTrue(village_result.is_valid)
        
        metadata_result = validator.validate_metadata(test_metadata)
        self.assertTrue(metadata_result.is_valid)

if __name__ == '__main__':
    unittest.main()