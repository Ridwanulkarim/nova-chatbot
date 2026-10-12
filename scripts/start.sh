#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=========================================="
echo "    Launching Nova AI Full-Stack Platform"
echo "=========================================="

trap 'kill $(jobs -p)' EXIT

# Start backend
./scripts/start_backend.sh &
BACKEND_PID=$!

# Wait for backend health check
echo "Waiting for backend to be ready..."
sleep 2

# Start frontend
./scripts/start_frontend.sh &
FRONTEND_PID=$!

echo "Nova AI is running!"
echo "- Frontend: http://localhost:5180"
echo "- Backend API & Swagger: http://127.0.0.1:8000/docs"
echo "Press Ctrl+C to terminate both servers."

wait
