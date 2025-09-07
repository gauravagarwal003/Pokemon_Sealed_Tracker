#!/bin/bash

# Pokemon Transaction Tracker - FastAPI Web App Runner
# This script installs dependencies and runs the FastAPI transaction tracker

echo "🃏 Pokemon Transaction Tracker (FastAPI)"
echo "========================================"

# Check if we're in a virtual environment or activate existing one
if [[ -z "$VIRTUAL_ENV" ]]; then
    if [ -d "venv" ]; then
        echo "📂 Activating existing virtual environment..."
        source venv/bin/activate
    else
        echo "❌ Error: Virtual environment not found."
        echo "💡 Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
else
    echo "✅ Virtual environment already active: $VIRTUAL_ENV"
fi

# Set the Python executable path
PYTHON_EXEC="venv/bin/python"

# Check if required packages are installed
echo "🔍 Checking if FastAPI is installed..."
$PYTHON_EXEC -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required packages in virtual environment..."
    $PYTHON_EXEC -m pip install -r requirements.txt
    
    # Check if installation was successful
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to install required packages."
        exit 1
    fi
else
    echo "📦 Installing/updating required packages in virtual environment..."
    $PYTHON_EXEC -m pip install -r requirements.txt
fi

echo ""
echo "🚀 Starting Pokemon Transaction Tracker..."
echo "📱 The web app will be available at: http://localhost:8000"
echo "🛑 Use Ctrl+C to stop the server."
echo ""

# Run the FastAPI app using python from virtual environment
$PYTHON_EXEC fastapi_app.py
