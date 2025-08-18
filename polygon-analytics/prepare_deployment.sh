#!/bin/bash

# Polygon Analytics Platform - Deployment Preparation Script
# This script prepares the application for AWS deployment

set -e

echo "🚀 Preparing Polygon Analytics Platform for AWS Deployment"
echo "=========================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if script is run from project root
if [ ! -f "requirements.txt" ] || [ ! -d "app" ] || [ ! -d "frontend" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Create deployment directory
DEPLOY_DIR="polygon-analytics-deploy"
rm -rf $DEPLOY_DIR
mkdir -p $DEPLOY_DIR

print_status "Created deployment directory: $DEPLOY_DIR"

# Copy application files
print_status "Copying application files..."
cp -r app $DEPLOY_DIR/
cp -r frontend $DEPLOY_DIR/
cp requirements.txt $DEPLOY_DIR/
cp docker-compose.yml $DEPLOY_DIR/

# Create .env template
cat > $DEPLOY_DIR/.env.template << 'EOF'
# API Keys (REPLACE WITH YOUR ACTUAL KEYS)
POLYGON_API_KEY=YOUR_POLYGON_API_KEY_HERE
OPENAI_API_KEY=YOUR_OPENAI_API_KEY_HERE

# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/polygon_analytics

# Redis Configuration
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-change-in-production

# Application Settings
APP_ENV=production
DEBUG=false
EOF

print_status "Created .env template"

# Create startup script
cat > $DEPLOY_DIR/start.sh << 'EOF'
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
EOF

chmod +x $DEPLOY_DIR/start.sh
print_status "Created startup script"

# Create stop script
cat > $DEPLOY_DIR/stop.sh << 'EOF'
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
EOF

chmod +x $DEPLOY_DIR/stop.sh
print_status "Created stop script"

# Create health check script
cat > $DEPLOY_DIR/health_check.sh << 'EOF'
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
EOF

chmod +x $DEPLOY_DIR/health_check.sh
print_status "Created health check script"

# Create deployment package
print_status "Creating deployment archive..."
tar -czf polygon-analytics-deploy.tar.gz $DEPLOY_DIR/

# Calculate package size
PACKAGE_SIZE=$(du -h polygon-analytics-deploy.tar.gz | cut -f1)

echo ""
echo "=========================================================="
echo -e "${GREEN}✅ Deployment package created successfully!${NC}"
echo ""
echo "Package: polygon-analytics-deploy.tar.gz"
echo "Size: $PACKAGE_SIZE"
echo ""
echo "Next steps:"
echo "1. Transfer the package to your EC2 instance:"
echo "   scp -i your-key.pem polygon-analytics-deploy.tar.gz ubuntu@<EC2-IP>:~/"
echo ""
echo "2. Extract on EC2:"
echo "   tar -xzf polygon-analytics-deploy.tar.gz"
echo "   cd polygon-analytics-deploy"
echo ""
echo "3. Configure environment:"
echo "   cp .env.template .env"
echo "   nano .env  # Add your API keys"
echo ""
echo "4. Start the application:"
echo "   ./start.sh"
echo ""
echo "5. Check health:"
echo "   ./health_check.sh"
echo "=========================================================="