# Polygon Analytics Platform

A powerful financial data analytics platform that fetches stock tick data from Polygon.io and uses AI (GPT-4o) to generate Python analytics templates from natural language prompts.

## Features

- 📊 **Real-time Data Fetching**: Pull tick-level stock data from Polygon.io API
- 🤖 **AI-Powered Analytics**: Generate Python code from plain English descriptions
- 💾 **Template Management**: Save and reuse analytics templates
- 📈 **Rich Visualizations**: Automatic chart and table generation
- ⚡ **High Performance**: Handles millions of tick records efficiently
- 🔄 **Template Library**: Pre-built templates for common analyses

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Polygon.io API key
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   cd polygon-analytics
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   - The `.env` file is already configured with your API keys

4. **Start services**
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

5. **Access the platform**
   - Web Interface: http://localhost:8501
   - API Documentation: http://localhost:8000/docs

## Usage Examples

### Fetch Stock Data
1. Open the web interface
2. Go to "Data Fetcher" page
3. Enter stock symbol (e.g., "AAPL")
4. Select date range
5. Click "Fetch Data"

### Generate Analytics Template
1. Go to "Analytics Generator" page
2. Enter a natural language prompt:
   - "Show me volume by hour for today with a bar chart"
   - "Calculate VWAP and show price vs VWAP over time"
   - "Display price distribution histogram"
3. Click "Generate Template"
4. Execute with your desired parameters

### Example Prompts

- **Volume Analysis**: "Show hourly trading volume with a bar chart"
- **VWAP Calculation**: "Calculate and plot VWAP against price"
- **Price Distribution**: "Create a histogram of price distribution"
- **Trade Statistics**: "Show average trade size by hour"
- **Volatility Analysis**: "Calculate and visualize price volatility"

## Architecture

```
polygon-analytics/
├── app/
│   ├── api/           # FastAPI endpoints
│   ├── models/        # Database models
│   ├── services/      # Business logic
│   ├── agents/        # LangChain AI agents
│   └── templates/     # Saved templates
├── frontend/          # Streamlit UI
└── docker-compose.yml # PostgreSQL & Redis
```

## API Endpoints

- `POST /api/fetch-data` - Fetch and store tick data
- `POST /api/generate-template` - Generate analytics template
- `POST /api/execute-template` - Execute template
- `GET /api/templates` - List saved templates
- `GET /api/data-summary` - Get data summary for symbol

## Database Schema

### tick_data
- `id`: Unique identifier
- `symbol`: Stock ticker
- `timestamp`: Trade timestamp
- `price`: Trade price
- `size`: Trade size
- `exchange`: Exchange code
- `conditions`: Trade conditions

### analytics_templates
- `id`: Template ID
- `name`: Template name
- `prompt`: Original prompt
- `python_code`: Generated code
- `output_type`: table/chart/both

## AWS Deployment

See [AWS_DEPLOYMENT_GUIDE.md](AWS_DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

### Quick Deploy
1. Launch EC2 t3.medium instance
2. Install Docker and Python
3. Upload application files
4. Configure environment variables
5. Start services with systemd

## Performance

- Handles 500M+ trades/day
- Sub-second template generation
- Optimized PostgreSQL queries
- Async data fetching
- Redis caching (optional)

## Troubleshooting

### Database Connection Error
```bash
docker-compose up -d
```

### API Not Starting
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Streamlit Issues
```bash
streamlit run frontend/app.py --server.port 8501
```

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.