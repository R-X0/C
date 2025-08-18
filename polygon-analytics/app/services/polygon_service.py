import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.config import get_settings
from app.models.models import TickData
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor

settings = get_settings()

class PolygonService:
    def __init__(self):
        self.api_key = settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
        
    async def fetch_trades(self, symbol: str, date: str, limit: int = 50000) -> List[Dict]:
        """Fetch trade data from Polygon API"""
        url = f"{self.base_url}/v3/trades/{symbol}"
        params = {
            "timestamp.gte": f"{date}T00:00:00Z",
            "timestamp.lt": f"{date}T23:59:59Z",
            "limit": limit,
            "apiKey": self.api_key
        }
        
        all_trades = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if "results" in data and data["results"]:
                    all_trades.extend(data["results"])
                
                if "next_url" in data and data["next_url"]:
                    url = data["next_url"]
                    params = {"apiKey": self.api_key}
                else:
                    break
                    
        return all_trades
    
    def save_trades_to_db(self, trades: List[Dict], symbol: str, db: Session):
        """Save trade data to database"""
        tick_data_objects = []
        
        for trade in trades:
            tick = TickData(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(trade.get("participant_timestamp", trade.get("sip_timestamp", 0)) / 1000000000),
                price=trade.get("price", 0),
                size=trade.get("size", 0),
                exchange=trade.get("exchange", ""),
                conditions=trade.get("conditions", [])
            )
            tick_data_objects.append(tick)
        
        if tick_data_objects:
            db.bulk_save_objects(tick_data_objects)
            db.commit()
            
        return len(tick_data_objects)
    
    async def fetch_and_store_data(self, symbol: str, start_date: str, end_date: str, db: Session):
        """Fetch data for a date range and store in database"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        total_records = 0
        current = start
        
        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            print(f"Fetching data for {symbol} on {date_str}")
            
            trades = await self.fetch_trades(symbol, date_str)
            if trades:
                records = self.save_trades_to_db(trades, symbol, db)
                total_records += records
                print(f"Saved {records} trades for {date_str}")
            
            current += timedelta(days=1)
        
        return total_records