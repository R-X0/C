#!/bin/bash

# Startup script for Polygon Analytics Platform

echo "Starting Polygon Analytics Platform..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Start Docker containers
echo "Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 10

# Check if PostgreSQL is ready
until docker exec polygon-analytics-postgres-1 pg_isready -U postgres > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done

echo "PostgreSQL is ready!"

# Check if Redis is ready
until docker exec polygon-analytics-redis-1 redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done

echo "Redis is ready!"

# Start FastAPI backend
echo "Starting FastAPI backend..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 > api.log 2>&1 &
echo $! > api.pid

# Start Streamlit frontend
echo "Starting Streamlit frontend..."
nohup streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true > streamlit.log 2>&1 &
echo $! > streamlit.pid

echo "✅ All services started successfully!"
echo "API: http://localhost:8000"
echo "Frontend: http://localhost:8501"
echo "API Docs: http://localhost:8000/docs"
