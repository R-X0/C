#!/bin/bash

# Health check script for Polygon Analytics Platform

echo "🔍 Checking service health..."

# Check FastAPI
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ | grep -q "200"; then
    echo "✅ FastAPI: Healthy"
else
    echo "❌ FastAPI: Not responding"
fi

# Check Streamlit
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/ | grep -q "200"; then
    echo "✅ Streamlit: Healthy"
else
    echo "❌ Streamlit: Not responding"
fi

# Check PostgreSQL
if docker exec polygon-analytics-postgres-1 pg_isready -U postgres > /dev/null 2>&1; then
    echo "✅ PostgreSQL: Healthy"
else
    echo "❌ PostgreSQL: Not responding"
fi

# Check Redis
if docker exec polygon-analytics-redis-1 redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Healthy"
else
    echo "❌ Redis: Not responding"
fi
