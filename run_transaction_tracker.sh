#!/bin/bash

# Pokemon Transaction Tracker - Streamlit App Runner
# This script installs dependencies and runs the Streamlit transaction tracker

echo "🃏 Pokemon Transaction Tracker"
echo "================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Install/upgrade required packages
echo "Installing required packages..."
pip3 install -r requirements.txt

# Check if installation was successful
if [ $? -ne 0 ]; then
    echo "Error: Failed to install required packages."
    exit 1
fi

echo ""
echo "Starting Pokemon Transaction Tracker..."
echo "The app will open in your default browser."
echo "Use Ctrl+C to stop the server."
echo ""

# Run the Streamlit app
streamlit run streamlit_app.py --server.port 8501 --server.address localhost
