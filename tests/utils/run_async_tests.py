"""
Wrapper script to run async tests with proper configuration
Workaround for Windows pytest-asyncio capture issues
"""

import subprocess
import sys
import os

def run_async_tests():
    """Run async tests with capture disabled"""
    test_files = [
        'tests/test_bot_alert_service.py',
        'tests/test_bot_handlers_callbacks.py',
    ]
    
    all_passed = True
    total_tests = 0
    passed_tests = 0
    
    for test_file in test_files:
        if not os.path.exists(test_file):
            print(f"Skipping {test_file} - file not found")
            continue
            
        print(f"\n{'='*60}")
        print(f"Running {test_file}")
        print(f"{'='*60}\n")
        
        # Run with capture disabled to avoid Windows issues
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_file, '-v', '--tb=short', '-s'],
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            all_passed = False
            print(f"\n[FAILED] {test_file} had failures")
        else:
            print(f"\n[PASSED] {test_file} passed")
            passed_tests += 1
        total_tests += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: {passed_tests}/{total_tests} test files passed")
    print(f"{'='*60}\n")
    
    return all_passed

if __name__ == '__main__':
    success = run_async_tests()
    sys.exit(0 if success else 1)

