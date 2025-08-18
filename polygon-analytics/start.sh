#!/bin/bash

echo "Starting Polygon Analytics Platform..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Start PostgreSQL and Redis
echo "Starting database services..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start FastAPI backend
echo "Starting API server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Wait for API to be ready
sleep 3

# Start Streamlit frontend
echo "Starting web interface..."
streamlit run frontend/app.py --server.port 8501 &

echo ""
echo "✅ Polygon Analytics Platform is running!"
echo ""
echo "📊 Web Interface: http://localhost:8501"
echo "🔧 API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait