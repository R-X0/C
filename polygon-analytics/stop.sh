#!/bin/bash

echo "Stopping Polygon Analytics Platform..."

# Stop Python processes
pkill -f "uvicorn app.main:app"
pkill -f "streamlit run"

# Stop Docker services
docker-compose down

echo "✅ All services stopped"