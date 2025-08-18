#!/bin/bash

# Stop script for Polygon Analytics Platform

echo "Stopping Polygon Analytics Platform..."

# Stop FastAPI
if [ -f api.pid ]; then
    kill $(cat api.pid) 2>/dev/null
    rm api.pid
    echo "Stopped FastAPI backend"
fi

# Stop Streamlit
if [ -f streamlit.pid ]; then
    kill $(cat streamlit.pid) 2>/dev/null
    rm streamlit.pid
    echo "Stopped Streamlit frontend"
fi

# Stop Docker containers
docker-compose down
echo "Stopped Docker containers"

echo "✅ All services stopped"
