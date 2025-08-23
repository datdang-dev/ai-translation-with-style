#!/usr/bin/env python3
"""
Tool to run all unittest and get coverage for services/ modules (except test_support)

This script will:
1. Find all test files in services/ modules (excluding test_support)
2. Run all tests with coverage
3. Generate comprehensive coverage reports
4. Display summary statistics

Author: datdang
Created: 2024-12-19
"""

import os
import sys
import subprocess
import glob
from pathlib import Path

# Color codes for better output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """Print a header with formatting"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def find_test_files():
    """Find all test files in services/ modules (excluding test_support)"""
    test_files = []
    services_path = Path("services")
    
    if not services_path.exists():
        print_error("services/ directory not found!")
        return []
    
    # Find all modules in services/
    for module_dir in services_path.iterdir():
        if not module_dir.is_dir():
            continue
        if module_dir.name.startswith("__"):
            continue
        if module_dir.name == "test_support":
            print_info(f"Skipping {module_dir.name} (excluded)")
            continue
        
        # Look for test files in each module
        module_test_files = []
        utest_dir = module_dir / "utest"
        
        if utest_dir.exists():
            # Find utest_*.py files
            utest_files = list(utest_dir.glob("utest_*.py"))
            module_test_files.extend(utest_files)
            
            # Find test_*.py files
            test_files_pattern = list(utest_dir.glob("test_*.py"))
            module_test_files.extend(test_files_pattern)
        
        if module_test_files:
            print_info(f"Found {len(module_test_files)} test file(s) in {module_dir.name}")
            for tf in module_test_files:
                print(f"    - {tf}")
            test_files.extend(module_test_files)
        else:
            print_warning(f"No test files found in {module_dir.name}")
    
    return test_files

def get_coverage_modules():
    """Get list of modules to include in coverage"""
    modules = []
    services_path = Path("services")
    
    for module_dir in services_path.iterdir():
        if not module_dir.is_dir():
            continue
        if module_dir.name.startswith("__"):
            continue
        if module_dir.name == "test_support":
            continue
        
        # Add the module to coverage
        modules.append(f"services.{module_dir.name}")
    
    return modules

def run_tests_with_coverage(test_files, coverage_modules):
    """Run all tests with coverage"""
    if not test_files:
        print_error("No test files found to run!")
        return False
    
    print_header("RUNNING TESTS WITH COVERAGE")
    
    # Build pytest command
    cmd = [
        "python3", "-m", "pytest",
        "-v",  # verbose
        "--tb=short",  # shorter traceback format
    ]
    
    # Add coverage options
    for module in coverage_modules:
        cmd.extend(["--cov", module])
    
    cmd.extend([
        "--cov-branch",  # include branch coverage
        "--cov-report=term-missing",  # show missing lines in terminal
        "--cov-report=html:services_coverage_html",  # generate HTML report
        "--cov-report=xml:services_coverage.xml",  # generate XML report
    ])
    
    # Add all test files
    for test_file in test_files:
        cmd.append(str(test_file))
    
    print_info(f"Running command: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(cmd, check=True, text=True)
        print_success("All tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Tests failed with exit code {e.returncode}")
        return False

def generate_summary_report():
    """Generate a summary report"""
    print_header("COVERAGE SUMMARY")
    
    html_report_path = Path("services_coverage_html/index.html")
    xml_report_path = Path("services_coverage.xml")
    
    if html_report_path.exists():
        print_success(f"HTML coverage report generated: {html_report_path.absolute()}")
    
    if xml_report_path.exists():
        print_success(f"XML coverage report generated: {xml_report_path.absolute()}")
    
    print_info("To view HTML coverage report, open: services_coverage_html/index.html")

def main():
    """Main function"""
    print_header("SERVICES COVERAGE TOOL")
    print_info("Running unittest and coverage for all services/ modules (except test_support)")
    
    # Check if we're in the right directory
    if not Path("services").exists():
        print_error("Please run this script from the project root directory (where services/ folder exists)")
        sys.exit(1)
    
    # Find test files
    print_header("DISCOVERING TEST FILES")
    test_files = find_test_files()
    
    if not test_files:
        print_warning("No test files found. Nothing to run.")
        sys.exit(0)
    
    print_success(f"Found total {len(test_files)} test file(s)")
    
    # Get coverage modules
    coverage_modules = get_coverage_modules()
    print_info(f"Coverage will include modules: {', '.join(coverage_modules)}")
    
    # Run tests with coverage
    success = run_tests_with_coverage(test_files, coverage_modules)
    
    if success:
        # Generate summary report
        generate_summary_report()
        print_header("COMPLETED SUCCESSFULLY")
        print_success("All tests passed and coverage reports generated!")
    else:
        print_header("COMPLETED WITH ERRORS")
        print_error("Some tests failed or coverage could not be generated")
        sys.exit(1)

if __name__ == "__main__":
    main()
