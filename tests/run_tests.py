"""
Test runner for Clash of Clans Upgrade Optimizer
"""

import unittest
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_unit_tests():
    """Run unit tests"""
    print("Running unit tests...")
    
    # Discover and run unit tests
    loader = unittest.TestLoader()
    test_dir = Path(__file__).parent / 'test_unit'
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests"""
    print("Running integration tests...")
    
    # Discover and run integration tests
    loader = unittest.TestLoader()
    test_dir = Path(__file__).parent / 'test_integration'
    suite = loader.discover(str(test_dir), pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_all_tests():
    """Run all tests"""
    print("Running all tests...")
    print("=" * 50)
    
    unit_success = run_unit_tests()
    integration_success = run_integration_tests()
    
    print("=" * 50)
    if unit_success and integration_success:
        print("✅ All tests passed!")
        return True
    else:
        print("❌ Some tests failed!")
        return False

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests for Clash of Clans Upgrade Optimizer')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    
    args = parser.parse_args()
    
    if args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    else:
        success = run_all_tests()
    
    sys.exit(0 if success else 1)