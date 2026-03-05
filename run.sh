#!/bin/bash
# Script to run YouTube All-in-One Downloader Pro

echo "Starting YouTube Downloader Pro..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "Checking dependencies..."
pip install -r requirements.txt -q

# Run the app with a production WSGI server
echo "Running the web server on http://0.0.0.0:5000 via Gunicorn"
gunicorn -w 4 -b 0.0.0.0:5000 app:app
