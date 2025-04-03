#!/usr/bin/env python3

import os
import subprocess
import sys
from datetime import datetime
import re

def write_error_log(test_dir, result):
    """Write error details to a log file in the module directory."""
    if result['failed'] > 0 or result['errors'] > 0:
        log_path = os.path.join(test_dir, 'coco_tb_error.log')
        with open(log_path, 'w') as f:
            f.write(f"Test Results for {result['name']}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Passed: {result['passed']}\n")
            f.write(f"Failed: {result['failed']}\n")
            f.write(f"Errors: {result['errors']}\n\n")
            
            # Extract error messages from output
            error_lines = []
            capture = False
            for line in result['output'].split('\n'):
                if 'ERROR' in line or 'FAIL' in line or 'Traceback' in line:
                    capture = True
                    error_lines.append(line)
                elif capture and line.strip():
                    error_lines.append(line)
                elif not line.strip():
                    capture = False
            
            f.write("Error Details:\n")
            f.write("-" * 80 + "\n")
            f.write('\n'.join(error_lines))

def write_summary_log(results):
    """Write a summary of all errors to the root directory."""
    with open('coco_tb_error_all.log', 'w') as f:
        f.write("Cocotb Test Summary Report\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        total_passed = sum(r['passed'] for r in results)
        total_failed = sum(r['failed'] for r in results)
        total_errors = sum(r['errors'] for r in results)
        
        f.write(f"Total Tests Run: {len(results)}\n")
        f.write(f"Total Passed: {total_passed}\n")
        f.write(f"Total Failed: {total_failed}\n")
        f.write(f"Total Errors: {total_errors}\n\n")
        
        for result in results:
            if result['failed'] > 0 or result['errors'] > 0:
                f.write(f"\nModule: {result['name']}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Passed: {result['passed']}\n")
                f.write(f"Failed: {result['failed']}\n")
                f.write(f"Errors: {result['errors']}\n\n")
                
                # Extract error messages
                error_lines = []
                capture = False
                for line in result['output'].split('\n'):
                    if 'ERROR' in line or 'FAIL' in line or 'Traceback' in line:
                        capture = True
                        error_lines.append(line)
                    elif capture and line.strip():
                        error_lines.append(line)
                    elif not line.strip():
                        capture = False
                
                f.write("Error Details:\n")
                f.write('\n'.join(error_lines))
                f.write("\n" + "=" * 80 + "\n")

def find_test_directories():
    """Find all directories containing cocotb testbenches."""
    test_dirs = []
    for item in os.listdir('.'):
        if os.path.isdir(item) and item.startswith('rr'):
            if os.path.exists(os.path.join(item, 'Makefile')):
                test_dirs.append(item)
    return sorted(test_dirs)

def run_test(test_dir):
    """Run a single testbench and return results."""
    print(f"\nRunning tests in {test_dir}...")
    
    # Change to test directory
    original_dir = os.getcwd()
    os.chdir(test_dir)
    
    try:
        # Run make clean first
        subprocess.run(['make', 'clean'], check=True, capture_output=True)
        
        # Run the test
        result = subprocess.run(['make'], capture_output=True, text=True)
        
        # Parse the output for test results
        output = result.stdout + result.stderr
        
        # Count passed and failed tests
        passed = len(re.findall(r'\*\*.*PASS.*\*\*', output))
        failed = len(re.findall(r'\*\*.*FAIL.*\*\*', output))
        
        # Check for any errors
        errors = len(re.findall(r'ERROR', output))
        
        # Get test name from Makefile
        with open('Makefile', 'r') as f:
            makefile = f.read()
            test_name = re.search(r'COCOTB_TEST_MODULES\s*=\s*(\w+)', makefile)
            if test_name:
                test_name = test_name.group(1)
            else:
                test_name = test_dir
        
        result_dict = {
            'name': test_name,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'output': output
        }
        
        # Write individual error log
        write_error_log(test_dir, result_dict)
        
        return result_dict
        
    except subprocess.CalledProcessError as e:
        result_dict = {
            'name': test_dir,
            'passed': 0,
            'failed': 1,
            'errors': 1,
            'output': e.stdout + e.stderr
        }
        write_error_log(test_dir, result_dict)
        return result_dict
    finally:
        # Return to original directory
        os.chdir(original_dir)

def main():
    """Main function to run all tests and report results."""
    print(f"Starting test run at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Find all test directories
    test_dirs = find_test_directories()
    if not test_dirs:
        print("No test directories found!")
        sys.exit(1)
    
    print(f"Found {len(test_dirs)} test directories:")
    for dir in test_dirs:
        print(f"  - {dir}")
    print("=" * 80)
    
    # Run all tests
    results = []
    total_passed = 0
    total_failed = 0
    total_errors = 0
    
    for test_dir in test_dirs:
        result = run_test(test_dir)
        results.append(result)
        
        total_passed += result['passed']
        total_failed += result['failed']
        total_errors += result['errors']
        
        # Print individual test results
        print(f"\nResults for {result['name']}:")
        print(f"  Passed: {result['passed']}")
        print(f"  Failed: {result['failed']}")
        print(f"  Errors: {result['errors']}")
        
        if result['failed'] > 0 or result['errors'] > 0:
            print("\nError output:")
            print(result['output'])
    
    # Write summary log
    write_summary_log(results)
    
    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary:")
    print(f"Total tests run: {len(test_dirs)}")
    print(f"Total passed: {total_passed}")
    print(f"Total failed: {total_failed}")
    print(f"Total errors: {total_errors}")
    print("\nDetailed error logs have been written to:")
    print("- Individual module directories: coco_tb_error.log")
    print("- Root directory: coco_tb_error_all.log")
    
    if total_failed == 0 and total_errors == 0:
        print("\nAll tests PASSED! 🎉")
        sys.exit(0)
    else:
        print("\nSome tests FAILED! 😢")
        sys.exit(1)

if __name__ == "__main__":
    main() 