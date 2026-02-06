#!/bin/bash

# Simple Backend Starter (No venv required)

echo "🚀 Starting YÖK Tez API Backend..."
echo "================================================"
echo ""
echo "🌐 Server: http://localhost:8000"
echo "📖 API Docs: http://localhost:8000/docs"
echo "🔍 Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo "================================================"
echo ""

cd backend
python3 -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
