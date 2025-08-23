#!/bin/bash
# Simple shell script to run services coverage
# Author: datdang
# Created: 2024-12-19

set -e  # Exit on any error

echo "🚀 Running Services Coverage Tool..."
echo "======================================="

# Check if we're in the right directory
if [ ! -d "services" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Run the Python coverage tool
python3 tools/run_services_coverage.py

echo ""
echo "✅ Services coverage tool completed!"
echo "📊 Check services_coverage_html/index.html for detailed coverage report"
