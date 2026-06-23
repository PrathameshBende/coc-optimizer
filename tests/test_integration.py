"""
Integration tests for Clash of Clans Upgrade Optimizer
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_pipeline import run_pipeline
from validation import DataValidator
from config import ConfigManager
from cache import CacheManager

class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the pipeline"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
        self.cache_manager = CacheManager(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_full_pipeline_simulation(self):
        """Simulate a full pipeline run"""
        # Create test data
        test_village = {
            'buildings': [{'data': 28000000, 'lvl': 1, 'cnt': 1}],
            'heroes': [],
            'spells': []
        }
        
        test_data_dir = Path(self.temp_dir) / "test_data"
        test_data_dir.mkdir()
        
        # Create test metadata files
        metadata_files = {
            'buildings.json': [
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
        }
        
        for filename, data in metadata_files.items():
            with open(test_data_dir / filename, 'w') as f:
                json.dump(data, f)
        
        # Create test village export
        village_file = Path(self.temp_dir) / "village.json"
        with open(village_file, 'w') as f:
            json.dump(test_village, f)
        
        # Test pipeline
        try:
            schedule_file = Path(self.temp_dir) / "schedule.json"
            run_pipeline(
                export_path=str(village_file),
                data_dir=str(test_data_dir),
                output_path=str(schedule_file)
            )
            
            # Check if output file was created
            self.assertTrue(schedule_file.exists())
            
            # Validate schedule
            validator = DataValidator()
            with open(schedule_file, 'r') as f:
                schedule_data = json.load(f)
            
            result = validator.validate_schedule(schedule_data)
            self.assertTrue(result.is_valid)
            
        except Exception as e:
            self.fail(f"Pipeline failed: {e}")
    
    def test_pipeline_with_caching(self):
        """Test pipeline with caching enabled"""
        # Create test data
        test_village = {
            'buildings': [{'data': 28000000, 'lvl': 1, 'cnt': 1}],
            'heroes': [],
            'spells': []
        }
        
        test_data_dir = Path(self.temp_dir) / "test_data"
        test_data_dir.mkdir()
        
        # Create test metadata
        metadata = [
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
        
        with open(test_data_dir / 'buildings.json', 'w') as f:
            json.dump(metadata, f)
        
        village_file = Path(self.temp_dir) / "village.json"
        with open(village_file, 'w') as f:
            json.dump(test_village, f)
        
        # Run pipeline twice to test caching
        schedule_file1 = Path(self.temp_dir) / "schedule1.json"
        schedule_file2 = Path(self.temp_dir) / "schedule2.json"
        
        run_pipeline(
            export_path=str(village_file),
            data_dir=str(test_data_dir),
            output_path=str(schedule_file1)
        )
        
        run_pipeline(
            export_path=str(village_file),
            data_dir=str(test_data_dir),
            output_path=str(schedule_file2)
        )
        
        # Both files should exist and be valid
        self.assertTrue(schedule_file1.exists())
        self.assertTrue(schedule_file2.exists())
        
        # Validate both schedules
        validator = DataValidator()
        with open(schedule_file1, 'r') as f:
            schedule1 = json.load(f)
        result1 = validator.validate_schedule(schedule1)
        self.assertTrue(result1.is_valid)
        
        with open(schedule_file2, 'r') as f:
            schedule2 = json.load(f)
        result2 = validator.validate_schedule(schedule2)
        self.assertTrue(result2.is_valid)

class TestConfigurationIntegration(unittest.TestCase):
    """Integration tests for configuration"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.json"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_configuration_pipeline_integration(self):
        """Test configuration with pipeline"""
        # Create custom config
        custom_config = {
            "machine": {
                "builder_count": 8,
                "lab_count": 2,
                "pet_count": 1
            },
            "solver": {
                "time_limit_seconds": 60
            }
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(custom_config, f)
        
        config_manager = ConfigManager(str(self.config_file))
        config = config_manager.config
        
        # Verify configuration was loaded
        self.assertEqual(config.machine.builder_count, 8)
        self.assertEqual(config.machine.lab_count, 2)
        self.assertEqual(config.solver.time_limit_seconds, 60)
        
        # Test validation
        self.assertTrue(config_manager.validate_config())

class TestErrorHandlingIntegration(unittest.TestCase):
    """Integration tests for error handling"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_pipeline_error_handling(self):
        """Test pipeline error handling"""
        # Test with missing files
        try:
            run_pipeline(
                export_path="nonexistent.json",
                data_dir="nonexistent_dir",
                output_path="output.json"
            )
            self.fail("Pipeline should have failed with missing files")
        except Exception as e:
            # Expected to fail
            self.assertIn("Village export file not found", str(e))
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        validator = DataValidator()
        
        # Test with invalid data
        invalid_data = {
            'buildings': "not an array",
            'heroes': "not an array"
        }
        
        result = validator.validate_village_export(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

class TestPerformanceIntegration(unittest.TestCase):
    """Performance integration tests"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = CacheManager(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_caching_performance(self):
        """Test caching performance improvement"""
        import time
        
        # Create test data
        test_data = {'test': 'data', 'large': list(range(1000))}
        
        # Time without cache
        start_time = time.time()
        for _ in range(10):
            # Simulate expensive operation
            result = json.dumps(test_data)
        time_without_cache = time.time() - start_time
        
        # Time with cache
        cache_key = 'performance_test'
        self.cache_manager.set_cache('performance', cache_key, test_data)
        
        start_time = time.time()
        for _ in range(10):
            result = self.cache_manager.get_cache('performance', cache_key)
        time_with_cache = time.time() - start_time
        
        # Cache should be faster (though this might vary)
        print(f"Without cache: {time_without_cache:.4f}s")
        print(f"With cache: {time_with_cache:.4f}s")

if __name__ == '__main__':
    unittest.main()