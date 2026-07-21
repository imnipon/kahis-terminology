#!/bin/bash
# Stop script for SA-PDT & SNOMED CT Veterinary Extension App
echo "Stopping SA-PDT & SNOMED CT Veterinary Extension..."

# Kill process listening on port 8080
PID=$(lsof -t -i:8080 2>/dev/null)
if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null || true
    echo "Killed server process PID: $PID"
fi

pkill -f "python3 server.py" 2>/dev/null || true
echo "App stopped successfully."
