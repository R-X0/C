# 📈 Polygon Analytics Platform - AWS Deployment Guide

## ✅ Application Overview
A fully functional platform that:
- Fetches millions of tick data from Polygon API
- Uses OpenAI GPT-4 to generate Python analytics templates from natural language
- Executes templates and displays results as tables and charts
- Saves templates for reuse

## 🔑 AWS Account Access
```
Email: findingsolutions2026@gmail.com
Password: AlphaStrategies00@
```

## 🚀 STEP-BY-STEP DEPLOYMENT INSTRUCTIONS

### Step 1: Launch EC2 Instance

1. **Login to AWS Console**
   - Go to https://console.aws.amazon.com
   - Use the credentials above

2. **Navigate to EC2**
   - Services → EC2 → Launch Instance

3. **Configure Instance**
   ```
   Name: polygon-analytics-server
   AMI: Ubuntu Server 22.04 LTS (64-bit x86)
   Instance Type: t3.medium (Recommended) or t3.large (For heavy usage)
   
   Key Pair:
   - Create new key pair
   - Name: polygon-analytics-key
   - Type: RSA
   - Format: .pem
   - Download and save securely!
   
   Network Settings:
   - Allow SSH from: My IP
   - Allow HTTP from: Anywhere (0.0.0.0/0)
   - Allow HTTPS from: Anywhere (0.0.0.0/0)
   
   Configure Storage:
   - 30 GB gp3
   
   Advanced Details:
   - User data (paste this):
   ```
   ```bash
   #!/bin/bash
   apt-get update
   apt-get install -y docker.io docker-compose python3-pip git nginx
   usermod -aG docker ubuntu
   ```

4. **Add Security Group Rules**
   - Click "Edit" in Network settings
   - Add rules:
     ```
     Type: Custom TCP | Port: 8000 | Source: 0.0.0.0/0 | Description: FastAPI
     Type: Custom TCP | Port: 8501 | Source: 0.0.0.0/0 | Description: Streamlit
     Type: Custom TCP | Port: 5432 | Source: Security Group ID | Description: PostgreSQL
     Type: Custom TCP | Port: 6379 | Source: Security Group ID | Description: Redis
     ```

5. **Launch Instance**
   - Click "Launch Instance"
   - Wait for instance to be "Running"
   - Note the Public IPv4 address

### Step 2: Connect to EC2

1. **Set key permissions** (on your local machine):
   ```bash
   chmod 400 polygon-analytics-key.pem
   ```

2. **SSH into instance**:
   ```bash
   ssh -i polygon-analytics-key.pem ubuntu@<YOUR-EC2-PUBLIC-IP>
   ```

### Step 3: Setup Application on EC2

Run these commands after connecting via SSH:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker (if not already installed)
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker ubuntu
newgrp docker

# 3. Install Python and dependencies
sudo apt install python3-pip python3-venv git -y

# 4. Create application directory
mkdir ~/polygon-analytics
cd ~/polygon-analytics

# 5. Create all application files
# You'll need to copy all the code files here
# Option A: Use git clone if you have a repository
# Option B: Copy files manually (see below)
```

### Step 4: Upload Application Files

From your LOCAL machine (not EC2), run:

```bash
# Create a deployment package
cd /root/C/polygon-analytics
tar -czf polygon-analytics.tar.gz app/ frontend/ requirements.txt docker-compose.yml

# Upload to EC2
scp -i polygon-analytics-key.pem polygon-analytics.tar.gz ubuntu@<YOUR-EC2-PUBLIC-IP>:~/

# Extract on EC2 (run this on EC2)
ssh -i polygon-analytics-key.pem ubuntu@<YOUR-EC2-PUBLIC-IP>
cd ~/polygon-analytics
tar -xzf ~/polygon-analytics.tar.gz
```

### Step 5: Configure Environment

On EC2, create the `.env` file:

```bash
nano .env
```

Add this content (update with your RDS/ElastiCache endpoints if using):

```env
# API Keys
POLYGON_API_KEY=PwMifytmOWB6I_5IfFUzgRjvUK7nML7d
OPENAI_API_KEY=sk-proj-VQQql6p-m8L_VTASP5WnAODR1wPKszs5eD6HlUADlBp-BHYqENPlEvxDkOQnKnqz7DGx3W5FPJSIJnRGHczBJiHAE63HNUhBRjh0rKuEqBKRTxJSUJE-IxgA

# Database (Local Docker PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/polygon_analytics

# Redis (Local Docker Redis)
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### Step 6: Start Services with Docker

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Check if containers are running
docker ps

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Step 7: Run Application

```bash
# Start FastAPI backend (in one terminal/screen)
screen -S api
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Press Ctrl+A then D to detach

# Start Streamlit frontend (in another terminal/screen)
screen -S frontend
source venv/bin/activate
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
# Press Ctrl+A then D to detach

# To reattach to screens:
# screen -r api
# screen -r frontend
```

### Step 8: Setup Nginx (OPTIONAL but recommended)

```bash
sudo nano /etc/nginx/sites-available/default
```

Replace content with:

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    server_name _;
    
    # Main app (Streamlit)
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Streamlit websocket
    location /_stcore/stream {
        proxy_pass http://localhost:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # API endpoints
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # API docs
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_set_header Host $host;
    }
}
```

Restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

### Step 9: Create Startup Script

Create a script to start everything:

```bash
nano ~/start_polygon.sh
```

Add:

```bash
#!/bin/bash
cd ~/polygon-analytics

# Start Docker containers
docker-compose up -d

# Wait for services to be ready
sleep 10

# Activate virtual environment
source venv/bin/activate

# Start API in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &

# Start Streamlit in background
nohup streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &

echo "Services started!"
echo "API running on port 8000"
echo "Streamlit running on port 8501"
```

Make executable:
```bash
chmod +x ~/start_polygon.sh
```

### Step 10: Setup Auto-start on Boot

```bash
sudo nano /etc/systemd/system/polygon-analytics.service
```

Add:

```ini
[Unit]
Description=Polygon Analytics Platform
After=network.target docker.service

[Service]
Type=forking
User=ubuntu
WorkingDirectory=/home/ubuntu/polygon-analytics
ExecStart=/home/ubuntu/start_polygon.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable polygon-analytics
sudo systemctl start polygon-analytics
```

## 🎉 ACCESS YOUR APPLICATION

Once everything is running:

1. **Main Application**: 
   - http://<YOUR-EC2-PUBLIC-IP>
   - Or http://<YOUR-EC2-PUBLIC-IP>:8501

2. **API Documentation**: 
   - http://<YOUR-EC2-PUBLIC-IP>:8000/docs

## ✅ TEST THE DEPLOYMENT

1. **Check Services**:
   ```bash
   # Check Docker containers
   docker ps
   
   # Check if ports are listening
   sudo netstat -tlnp | grep -E '8000|8501'
   
   # Check logs
   tail -f ~/polygon-analytics/api.log
   tail -f ~/polygon-analytics/streamlit.log
   ```

2. **Test in Browser**:
   - Go to http://<YOUR-EC2-PUBLIC-IP>:8501
   - Click "Data Fetcher"
   - Enter: Symbol: AAPL
   - Select date range (use dates from last week)
   - Click "Fetch Data"
   - Wait for data to load
   - Go to "Analytics Generator"
   - Enter: "show me volume by hour with a bar chart"
   - Click "Generate Template"
   - Click "Execute Template"

## 🔧 TROUBLESHOOTING

**Cannot access application:**
```bash
# Check if services are running
ps aux | grep uvicorn
ps aux | grep streamlit

# Check firewall
sudo ufw status

# Restart services
cd ~/polygon-analytics
./start_polygon.sh
```

**Database connection error:**
```bash
# Check PostgreSQL
docker ps
docker logs polygon-analytics-postgres-1

# Restart containers
docker-compose down
docker-compose up -d
```

**Out of memory:**
```bash
# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## 💰 COST ESTIMATE

**Current Setup (Docker-based):**
- EC2 t3.medium: ~$30/month
- Storage: ~$3/month
- Data transfer: ~$5/month
- **Total: ~$40/month**

**Production Setup (with RDS/ElastiCache):**
- EC2 t3.large: ~$60/month
- RDS PostgreSQL: ~$15/month
- ElastiCache Redis: ~$13/month
- **Total: ~$90/month**

## 📝 MAINTENANCE

**View logs:**
```bash
tail -f ~/polygon-analytics/api.log
tail -f ~/polygon-analytics/streamlit.log
docker logs -f polygon-analytics-postgres-1
```

**Restart services:**
```bash
cd ~/polygon-analytics
docker-compose restart
./start_polygon.sh
```

**Update application:**
```bash
cd ~/polygon-analytics
# Upload new files
docker-compose down
docker-compose up -d
./start_polygon.sh
```

## 🚨 IMPORTANT NOTES

1. **API Keys**: The OpenAI key in .env needs to be kept secure
2. **Data Volume**: With millions of ticks, consider upgrading to t3.large
3. **Backup**: Set up regular database backups
4. **Monitoring**: Set up CloudWatch alarms for CPU/memory

## ✅ DEPLOYMENT CHECKLIST

- [ ] EC2 instance launched
- [ ] Security groups configured
- [ ] Application files uploaded
- [ ] .env file configured
- [ ] Docker containers running
- [ ] FastAPI accessible on port 8000
- [ ] Streamlit accessible on port 8501
- [ ] Test data fetch working
- [ ] Test template generation working
- [ ] Nginx configured (optional)
- [ ] Auto-start configured

---

**Your Polygon Analytics Platform should now be live!** 🎉

**Support**: If you encounter issues, check the logs first, then contact the development team.