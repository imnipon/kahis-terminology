#!/bin/bash
# Start script for SA-PDT & SNOMED CT Veterinary Extension App
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# Stop any old running instance first
pkill -f "python3 server.py" 2>/dev/null || true
sleep 1

echo "=================================================="
echo "Starting SA-PDT & SNOMED CT Veterinary Extension..."
echo "Running at: http://localhost:8080"
echo "=================================================="

python3 server.py
