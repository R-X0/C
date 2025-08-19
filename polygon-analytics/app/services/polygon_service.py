import httpx
from datetime import datetime
from typing import List, Dict
from app.config import get_settings
from sqlalchemy.orm import Session
import asyncio
import time
import psycopg2
import io
from asyncio import Queue, Semaphore
import aiohttp
from concurrent.futures import ThreadPoolExecutor

settings = get_settings()

class PolygonService:
    def __init__(self):
        self.api_key = settings.polygon_api_key
        self.base_url = "https://api.polygon.io"
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def fetch_page_ultra(self, session, url):
        """Ultra-fast fetch without semaphore"""
        try:
            async with session.get(url, params={"apiKey": self.api_key}) as response:
                return await response.json()
        except:
            return None
    
    def db_writer_thread(self, queue, symbol, conn):
        """Dedicated thread for DB writes"""
        total = 0
        buffer = []
        
        while True:
            item = queue.get()
            if item is None:
                break
            
            buffer.extend(item)
            
            # Write when buffer is large
            if len(buffer) >= 200000:
                total += self._sync_bulk_insert(buffer[:200000], symbol, conn)
                buffer = buffer[200000:]
        
        # Final flush
        if buffer:
            total += self._sync_bulk_insert(buffer, symbol, conn)
        
        return total
    
    def _sync_bulk_insert(self, trades, symbol, conn):
        """Synchronous bulk insert for thread"""
        if not trades:
            return 0
        
        buffer = io.StringIO()
        count = 0
        
        for trade in trades:
            ts = trade.get("participant_timestamp") or trade.get("sip_timestamp", 0)
            if not ts:
                continue
            
            seconds = ts // 1_000_000_000
            microseconds = (ts % 1_000_000_000) // 1000
            dt = datetime.utcfromtimestamp(seconds)
            
            buffer.write(
                f"{symbol}\t"
                f"{dt.strftime('%Y-%m-%d %H:%M:%S')}.{microseconds:06d}\t"
                f"{float(trade.get('price', 0))}\t"
                f"{int(float(trade.get('size', 0)))}\t"
                f"{trade.get('exchange', '') or ''}\t"
                f"{str(trade.get('conditions', []))}\n"
            )
            count += 1
        
        if count > 0:
            buffer.seek(0)
            cur = conn.cursor()
            cur.copy_from(
                buffer,
                'tick_data',
                columns=('symbol', 'timestamp', 'price', 'size', 'exchange', 'conditions'),
                sep='\t',
                size=16384
            )
            conn.commit()
            cur.close()
        
        buffer.close()
        return count
    
    async def pipeline_fetch(self, symbol: str, start_date: str, end_date: str, conn):
        """Pipeline architecture - fetch and write in parallel"""
        
        initial_url = f"{self.base_url}/v3/trades/{symbol}"
        initial_params = {
            "timestamp.gte": f"{start_date}T00:00:00Z",
            "timestamp.lte": f"{end_date}T23:59:59Z",
            "limit": 50000,
            "order": "asc"
        }
        
        # Ultra-high performance connector
        connector = aiohttp.TCPConnector(
            limit=500,
            limit_per_host=500,
            ttl_dns_cache=300,
            keepalive_timeout=30
        )
        
        timeout = aiohttp.ClientTimeout(total=30, connect=0.5, sock_read=5)
        
        # Queue for pipeline
        import queue
        write_queue = queue.Queue(maxsize=50)
        
        # Start DB writer thread
        from threading import Thread
        writer_thread = Thread(
            target=self.db_writer_thread,
            args=(write_queue, symbol, conn)
        )
        writer_thread.start()
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Get first page
            async with session.get(initial_url, params={**initial_params, "apiKey": self.api_key}) as resp:
                first_data = await resp.json()
            
            # Queue first batch
            if "results" in first_data:
                write_queue.put(first_data["results"])
            
            # Collect URLs
            all_urls = []
            if "next_url" in first_data:
                all_urls.append(first_data["next_url"])
            
            # Pre-fetch phase - get initial URLs quickly
            if all_urls:
                prefetch_batch = all_urls[:10]
                all_urls = all_urls[10:]
                
                tasks = [self.fetch_page_ultra(session, url) for url in prefetch_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if result and not isinstance(result, Exception):
                        if "results" in result:
                            write_queue.put(result["results"])
                        if "next_url" in result:
                            all_urls.append(result["next_url"])
            
            # Main fetch loop - ABSOLUTE MAXIMUM PARALLELISM
            while all_urls:
                # Fetch 500 pages at once - PUSH THE LIMITS!
                batch_size = min(500, len(all_urls))
                batch = all_urls[:batch_size]
                all_urls = all_urls[batch_size:]
                
                # Create all tasks without semaphore
                tasks = [self.fetch_page_ultra(session, url) for url in batch]
                
                # Execute ALL at once
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                new_urls = []
                for result in results:
                    if result and not isinstance(result, Exception):
                        if "results" in result:
                            write_queue.put(result["results"])
                        if "next_url" in result:
                            new_urls.append(result["next_url"])
                
                all_urls.extend(new_urls)
        
        # Signal writer to stop
        write_queue.put(None)
        writer_thread.join()
        
        return 0  # Return value handled by thread
    
    def _get_db_connection(self):
        """Get optimized psycopg2 connection"""
        db_url = settings.database_url
        if db_url.startswith("postgresql://"):
            db_url = db_url[13:]
        
        parts = db_url.split("@")
        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")
        host_port = host_db[0].split(":")
        
        conn = psycopg2.connect(
            host=host_port[0],
            port=host_port[1],
            database=host_db[1],
            user=user_pass[0],
            password=user_pass[1],
            options='-c synchronous_commit=off -c work_mem=512MB -c maintenance_work_mem=512MB'
        )
        conn.set_session(autocommit=False)
        return conn
    
    async def fetch_and_store_data(self, symbol: str, start_date: str, end_date: str, db: Session):
        """ULTIMATE PIPELINE - 300 CONCURRENT REQUESTS + PARALLEL DB WRITES"""
        start_time = time.time()
        
        # Clear data
        from sqlalchemy import text
        db.execute(text("""
            DELETE FROM tick_data 
            WHERE symbol = :symbol 
            AND timestamp BETWEEN :start_ts AND :end_ts
        """), {
            "symbol": symbol,
            "start_ts": f"{start_date} 00:00:00",
            "end_ts": f"{end_date} 23:59:59"
        })
        db.commit()
        
        # Get DB connection
        conn = self._get_db_connection()
        
        # Pipeline fetch
        await self.pipeline_fetch(symbol, start_date, end_date, conn)
        
        # Count records
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM tick_data 
            WHERE symbol = %s 
            AND timestamp BETWEEN %s AND %s
        """, (symbol, f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
        total_records = cur.fetchone()[0]
        cur.close()
        
        conn.close()
        
        elapsed = time.time() - start_time
        records_per_second = total_records / elapsed if elapsed > 0 else 0
        
        print(f"\n{'='*60}")
        print(f"⚡⚡⚡ ULTIMATE PIPELINE ARCHITECTURE!")
        print(f"   500 CONCURRENT API REQUESTS")
        print(f"   PARALLEL DB WRITES")
        print(f"   Records: {total_records:,}")
        print(f"   Time: {elapsed:.1f} seconds")
        print(f"   Speed: {records_per_second:,.0f} records/second")
        if total_records > 0:
            seconds_per_million = (elapsed / (total_records / 1_000_000))
            print(f"   📊 {seconds_per_million:.1f} seconds per million records")
            if seconds_per_million < 10:
                print(f"   🔥 UNDER 10 SECONDS PER MILLION!")
            if seconds_per_million < 5:
                print(f"   ⚡⚡⚡ UNDER 5 SECONDS PER MILLION!")
        print(f"{'='*60}\n")
        
        return total_records