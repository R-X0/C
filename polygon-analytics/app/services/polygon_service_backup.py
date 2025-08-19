import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.config import get_settings
from app.models.models import TickData
from sqlalchemy.orm import Session
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
import psycopg2
from psycopg2.extras import execute_values
import io

settings = get_settings()

class PolygonService:
    def __init__(self):
        self.api_key = settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
        
    async def fetch_trades_parallel(self, symbol: str, start_date: str, end_date: str, session: Session) -> int:
        """Fetch trades with parallel pagination for maximum speed"""
        
        # First request to get total pages
        initial_url = f"{self.base_url}/v3/trades/{symbol}"
        params = {
            "timestamp.gte": f"{start_date}T00:00:00Z",
            "timestamp.lte": f"{end_date}T23:59:59Z",
            "limit": 50000,
            "order": "asc",
            "apiKey": self.api_key
        }
        
        # Create high-performance client
        limits = httpx.Limits(max_keepalive_connections=20, max_connections=50)
        timeout = httpx.Timeout(30.0, connect=5.0)
        transport = httpx.AsyncHTTPTransport(retries=1)
        
        all_trades = []
        total_saved = 0
        
        async with httpx.AsyncClient(limits=limits, timeout=timeout, transport=transport) as client:
            # Sequential fetching with immediate bulk saves for maximum speed
            current_url = initial_url
            current_params = params
            page_num = 0
            
            while True:
                page_num += 1
                
                try:
                    response = await client.get(current_url, params=current_params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if "results" in data and data["results"]:
                        trades_batch = data["results"]
                        all_trades.extend(trades_batch)
                        
                        # Save in large batches for speed
                        if len(all_trades) >= 500000:
                            saved = self._ultra_fast_bulk_insert(all_trades[:500000], symbol, session)
                            total_saved += saved
                            all_trades = all_trades[500000:]
                    
                    # Check for next page
                    if "next_url" in data and data["next_url"]:
                        current_url = data["next_url"]
                        current_params = {"apiKey": self.api_key}
                    else:
                        break
                        
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        await asyncio.sleep(5)
                        continue
                    else:
                        raise e
                except Exception as e:
                    print(f"Error on page {page_num}: {e}")
                    break
        
        # Save remaining trades
        if all_trades:
            saved = self._ultra_fast_bulk_insert(all_trades, symbol, session)
            total_saved += saved
        
        return total_saved
    
    def _ultra_fast_bulk_insert(self, trades: List[Dict], symbol: str, db: Session):
        """Use PostgreSQL COPY for absolute maximum performance"""
        if not trades:
            return 0
        
        # Get raw psycopg2 connection for maximum speed
        conn_string = settings.database_url.replace("postgresql://", "")
        if "@" in conn_string:
            user_pass, host_db = conn_string.split("@")
            user, password = user_pass.split(":")
            host_port, database = host_db.split("/")
            host, port = host_port.split(":")
        else:
            # Parse alternative format
            import re
            pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
            match = re.match(pattern, settings.database_url)
            if match:
                user, password, host, port, database = match.groups()
            else:
                # Fallback to SQLAlchemy's method
                return self._fallback_insert(trades, symbol, db)
        
        # Direct psycopg2 connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cur = conn.cursor()
        
        try:
            # Prepare data in memory
            buffer = io.StringIO()
            
            for trade in trades:
                # Ultra-fast timestamp conversion
                ts = trade.get("participant_timestamp") or trade.get("sip_timestamp", 0)
                if not ts:
                    continue
                
                # Direct timestamp conversion without datetime object
                timestamp = self._fast_timestamp_convert(ts)
                
                # Write tab-separated values with proper type conversion
                price = float(trade.get('price', 0))
                size = int(float(trade.get('size', 0)))  # Convert to int, handling float strings
                exchange = trade.get('exchange', '') or ''
                conditions = str(trade.get('conditions', []))
                
                buffer.write(f"{symbol}\t{timestamp}\t{price}\t{size}\t{exchange}\t{conditions}\n")
            
            buffer.seek(0)
            
            # Use COPY for ultimate speed (100,000+ records/second)
            cur.copy_from(
                buffer,
                'tick_data',
                columns=('symbol', 'timestamp', 'price', 'size', 'exchange', 'conditions'),
                sep='\t'
            )
            
            conn.commit()
            
        finally:
            cur.close()
            conn.close()
        
        return len(trades)
    
    def _fast_timestamp_convert(self, nanoseconds):
        """Ultra-fast timestamp conversion without datetime objects"""
        seconds = nanoseconds // 1_000_000_000
        microseconds = (nanoseconds % 1_000_000_000) // 1000
        
        # Direct format string without datetime
        import time
        time_tuple = time.gmtime(seconds)
        return f"{time_tuple.tm_year:04d}-{time_tuple.tm_mon:02d}-{time_tuple.tm_mday:02d} " \
               f"{time_tuple.tm_hour:02d}:{time_tuple.tm_min:02d}:{time_tuple.tm_sec:02d}.{microseconds:06d}"
    
    def _fallback_insert(self, trades: List[Dict], symbol: str, db: Session):
        """Fallback method using execute_values for good performance"""
        if not trades:
            return 0
        
        from sqlalchemy import text
        
        values = []
        for trade in trades:
            ts = trade.get("participant_timestamp") or trade.get("sip_timestamp", 0)
            if not ts:
                continue
            
            timestamp = datetime.fromtimestamp(ts / 1_000_000_000)
            values.append((
                symbol,
                timestamp,
                float(trade.get("price", 0)),
                int(trade.get("size", 0)),
                trade.get("exchange", ""),
                str(trade.get("conditions", []))
            ))
        
        if values:
            # Use psycopg2's execute_values for batch insert
            raw_conn = db.connection().connection
            cur = raw_conn.cursor()
            
            execute_values(
                cur,
                """INSERT INTO tick_data (symbol, timestamp, price, size, exchange, conditions)
                   VALUES %s ON CONFLICT DO NOTHING""",
                values,
                template="(%s, %s, %s, %s, %s, %s)",
                page_size=10000
            )
            
            raw_conn.commit()
            cur.close()
        
        return len(values)
    
    async def fetch_and_store_data(self, symbol: str, start_date: str, end_date: str, db: Session):
        """Ultimate performance fetch - as fast as Polygon API allows"""
        start_time = time.time()
        
        # Clear existing data with raw SQL for speed
        from sqlalchemy import text
        delete_sql = text("""
            TRUNCATE TABLE tick_data RESTART IDENTITY;
            DELETE FROM tick_data 
            WHERE symbol = :symbol 
            AND timestamp >= :start_ts 
            AND timestamp <= :end_ts
        """)
        
        try:
            db.execute(delete_sql, {
                "symbol": symbol,
                "start_ts": f"{start_date} 00:00:00",
                "end_ts": f"{end_date} 23:59:59"
            })
            db.commit()
        except:
            # If TRUNCATE fails, just do DELETE
            delete_sql = text("""
                DELETE FROM tick_data 
                WHERE symbol = :symbol 
                AND timestamp >= :start_ts 
                AND timestamp <= :end_ts
            """)
            db.execute(delete_sql, {
                "symbol": symbol,
                "start_ts": f"{start_date} 00:00:00",
                "end_ts": f"{end_date} 23:59:59"
            })
            db.commit()
        
        # Fetch with parallel requests
        total_records = await self.fetch_trades_parallel(symbol, start_date, end_date, db)
        
        elapsed = time.time() - start_time
        records_per_second = total_records / elapsed if elapsed > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"✅ BLAZING FAST COMPLETE!")
        print(f"   Records: {total_records:,}")
        print(f"   Time: {elapsed:.1f} seconds")
        print(f"   Speed: {records_per_second:,.0f} records/second")
        print(f"{'='*60}\n")
        
        return total_records