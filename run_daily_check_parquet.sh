#!/bin/bash

# Daily Pokemon Sealed Products Price Checker - Parquet Version
# This script should be run daily (e.g., via cron job) to track price changes
# Uses efficient Parquet format for fast storage and analysis

echo "=== Pokemon Sealed Products Daily Price Check (Parquet) ===" 
echo "Date: $(date)"
echo ""

# Navigate to the script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run the Parquet-based daily price checker
echo "Running daily price check (Parquet format)..."
python daily_price_checker_parquet.py

echo ""
echo "=== Price check completed ===" 
echo ""

echo ""
echo "=== Daily Parquet price tracking completed at $(date) ==="

# Optional: Show storage efficiency
if [ -d "daily_prices" ]; then
    echo ""
    echo "📊 Storage Summary:"
    total_size=$(du -sh daily_prices | cut -f1)
    file_count=$(find daily_prices -name "*.parquet" | wc -l)
    echo "   Total Parquet files: $file_count"
    echo "   Total storage used: $total_size"
fi
