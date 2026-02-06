#!/bin/bash

# Start YÖK Tez Frontend Development Server

echo "🎨 Starting YÖK Tez Frontend..."
echo "================================================"
echo ""

# Check if Python http.server is available
if command -v python3 &> /dev/null; then
    echo "✅ Python3 found"
    echo "🌐 Frontend will be available at: http://localhost:3000"
    echo ""
    echo "Press Ctrl+C to stop the server"
    echo "================================================"
    echo ""

    cd frontend
    python3 -m http.server 3000
else
    echo "❌ Python3 not found. Please install Python 3."
    exit 1
fi
