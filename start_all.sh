#!/bin/bash

# Start both Backend and Frontend in separate terminals

echo "🚀 Starting YÖK Tez Application..."
echo "================================================"
echo ""

# Check if tmux is available
if command -v tmux &> /dev/null; then
    echo "Using tmux to run both servers..."

    # Create a new tmux session
    tmux new-session -d -s yok-tez

    # Split the window
    tmux split-window -h

    # Run backend in first pane
    tmux send-keys -t yok-tez:0.0 './start_backend.sh' C-m

    # Run frontend in second pane
    tmux send-keys -t yok-tez:0.1 './start_frontend.sh' C-m

    # Attach to the session
    tmux attach-session -t yok-tez

elif command -v gnome-terminal &> /dev/null; then
    echo "Using gnome-terminal..."
    gnome-terminal -- bash -c './start_backend.sh; exec bash'
    sleep 2
    gnome-terminal -- bash -c './start_frontend.sh; exec bash'

    echo "✅ Servers started in separate terminals"
    echo "Backend: http://localhost:8000"
    echo "Frontend: http://localhost:3000"

else
    echo "⚠️  No terminal multiplexer found."
    echo "Please run the following commands in separate terminals:"
    echo ""
    echo "Terminal 1: ./start_backend.sh"
    echo "Terminal 2: ./start_frontend.sh"
    echo ""
fi
