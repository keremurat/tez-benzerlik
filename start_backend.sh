#!/bin/bash

# Start YÖK Tez API Backend Server

echo "🚀 Starting YÖK Tez API Backend..."
echo "================================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "✅ Virtual environment activated"
echo ""

# Start the FastAPI server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔍 Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

cd backend
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
