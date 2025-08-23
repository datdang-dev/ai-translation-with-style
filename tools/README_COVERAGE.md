# Services Coverage Tools

## Overview

This directory contains tools to run unittest and generate coverage reports for all modules in the `services/` directory (excluding `test_support`).

## Available Tools

### 1. Python Tool: `run_services_coverage.py`

**Features:**
- ✅ Automatically discovers all test files in services modules
- ✅ Runs all tests with comprehensive coverage
- ✅ Generates HTML and XML coverage reports
- ✅ Colored output for better readability
- ✅ Detailed summary and statistics

**Usage:**
```bash
python3 tools/run_services_coverage.py
```

### 2. Shell Script: `run_services_coverage.sh`

**Features:**
- ✅ Simple wrapper around the Python tool
- ✅ Quick and easy to run
- ✅ Executable from anywhere in the project

**Usage:**
```bash
./tools/run_services_coverage.sh
```

## Generated Reports

After running the tools, you'll get:

1. **HTML Report**: `services_coverage_html/index.html`
   - Interactive HTML coverage report
   - Shows line-by-line coverage
   - Branch coverage information
   - Easy to navigate and share

2. **XML Report**: `services_coverage.xml`
   - Machine-readable format
   - Suitable for CI/CD integration
   - Compatible with coverage tools

3. **Terminal Output**: Real-time coverage summary in terminal

## Current Coverage Status

As of latest run:

| Module | Statements | Coverage |
|--------|------------|----------|
| `services/common/error_codes.py` | 8 | 100% |
| `services/key_manager/key_manager.py` | 50 | 100% |
| `services/request_handler/request_handler.py` | 33 | 100% |
| **TOTAL** | **91** | **100%** |

## Modules Included

- ✅ `services/common/` - Common utilities and error codes
- ✅ `services/key_manager/` - API key management functionality  
- ✅ `services/request_handler/` - Request handling and retry logic
- ❌ `services/test_support/` - Excluded (test utilities)

## Requirements

- Python 3.12+
- pytest
- pytest-cov
- pytest-asyncio

Install with:
```bash
pip install -r requirements-dev.txt
```

## How It Works

1. **Discovery Phase**: Scans `services/` directory for modules (excluding `test_support`)
2. **Test Detection**: Finds `utest_*.py` and `test_*.py` files in each module's `utest/` directory
3. **Coverage Execution**: Runs pytest with coverage for all discovered tests and modules
4. **Report Generation**: Creates HTML, XML and terminal coverage reports
5. **Summary**: Displays results and file locations

## Future Enhancements

- [ ] Add coverage threshold validation
- [ ] Integration with CI/CD pipelines
- [ ] Coverage trend tracking
- [ ] Email notifications for coverage drops
- [ ] Support for custom exclude patterns

## Troubleshooting

### No test files found
- Ensure test files follow naming convention: `utest_*.py` or `test_*.py`
- Check that test files are in `module/utest/` directory

### Import errors
- Run from project root directory (where `services/` folder exists)
- Ensure all dependencies are installed

### Permission denied
- Make shell script executable: `chmod +x tools/run_services_coverage.sh`

## Author

Created by: datdang  
Date: 2024-12-19  
Purpose: Comprehensive testing and coverage for services modules
