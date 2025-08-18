"""Example analytics templates for common use cases"""

VOLUME_BY_HOUR = """
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from io import BytesIO
import base64

def analyze_data(db_session, symbol, start_date, end_date):
    # Query tick data
    query = text('''
        SELECT 
            DATE_TRUNC('hour', timestamp) as hour,
            SUM(size) as total_volume,
            COUNT(*) as trade_count,
            AVG(price) as avg_price
        FROM tick_data
        WHERE symbol = :symbol 
            AND timestamp BETWEEN :start AND :end
        GROUP BY hour
        ORDER BY hour
    ''')
    
    result = db_session.execute(query, {
        'symbol': symbol,
        'start': start_date,
        'end': end_date
    })
    
    df = pd.DataFrame(result.fetchall(), columns=['hour', 'total_volume', 'trade_count', 'avg_price'])
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Volume chart
    ax1.bar(df['hour'], df['total_volume'], color='steelblue', alpha=0.7)
    ax1.set_xlabel('Hour')
    ax1.set_ylabel('Total Volume')
    ax1.set_title(f'{symbol} - Volume by Hour')
    ax1.grid(True, alpha=0.3)
    
    # Trade count chart
    ax2.plot(df['hour'], df['trade_count'], marker='o', color='green')
    ax2.set_xlabel('Hour')
    ax2.set_ylabel('Number of Trades')
    ax2.set_title(f'{symbol} - Trade Count by Hour')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)
    
    return {
        'type': 'both',
        'data': df.to_dict('records'),
        'chart': img_str
    }
"""

VWAP_CALCULATION = """
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from io import BytesIO
import base64
import numpy as np

def analyze_data(db_session, symbol, start_date, end_date):
    # Query tick data
    query = text('''
        SELECT timestamp, price, size
        FROM tick_data
        WHERE symbol = :symbol 
            AND timestamp BETWEEN :start AND :end
        ORDER BY timestamp
    ''')
    
    result = db_session.execute(query, {
        'symbol': symbol,
        'start': start_date,
        'end': end_date
    })
    
    df = pd.DataFrame(result.fetchall(), columns=['timestamp', 'price', 'size'])
    
    # Calculate VWAP
    df['price_volume'] = df['price'] * df['size']
    df['cumulative_pv'] = df['price_volume'].cumsum()
    df['cumulative_volume'] = df['size'].cumsum()
    df['vwap'] = df['cumulative_pv'] / df['cumulative_volume']
    
    # Resample to 5-minute intervals for cleaner visualization
    df.set_index('timestamp', inplace=True)
    resampled = df.resample('5T').agg({
        'price': 'mean',
        'vwap': 'last',
        'size': 'sum'
    }).dropna()
    
    # Create visualization
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(resampled.index, resampled['price'], label='Price', alpha=0.7, linewidth=1)
    ax.plot(resampled.index, resampled['vwap'], label='VWAP', color='red', linewidth=2)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Price ($)')
    ax.set_title(f'{symbol} - Price vs VWAP')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Format x-axis
    fig.autofmt_xdate()
    
    # Convert to base64
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)
    
    # Summary statistics
    summary = pd.DataFrame({
        'Metric': ['Total Volume', 'Average Price', 'VWAP', 'Price Std Dev'],
        'Value': [
            df['size'].sum(),
            df['price'].mean(),
            df['vwap'].iloc[-1] if len(df) > 0 else 0,
            df['price'].std()
        ]
    })
    
    return {
        'type': 'both',
        'data': summary.to_dict('records'),
        'chart': img_str
    }
"""

PRICE_DISTRIBUTION = """
import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import text
from io import BytesIO
import base64
import numpy as np

def analyze_data(db_session, symbol, start_date, end_date):
    # Query tick data
    query = text('''
        SELECT price, size
        FROM tick_data
        WHERE symbol = :symbol 
            AND timestamp BETWEEN :start AND :end
    ''')
    
    result = db_session.execute(query, {
        'symbol': symbol,
        'start': start_date,
        'end': end_date
    })
    
    df = pd.DataFrame(result.fetchall(), columns=['price', 'size'])
    
    # Statistical analysis
    stats = {
        'Mean Price': df['price'].mean(),
        'Median Price': df['price'].median(),
        'Std Dev': df['price'].std(),
        'Min Price': df['price'].min(),
        'Max Price': df['price'].max(),
        'Total Volume': df['size'].sum(),
        'Trade Count': len(df)
    }
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Price distribution histogram
    ax1.hist(df['price'], bins=50, color='skyblue', edgecolor='black', alpha=0.7)
    ax1.axvline(stats['Mean Price'], color='red', linestyle='--', label=f"Mean: ${stats['Mean Price']:.2f}")
    ax1.axvline(stats['Median Price'], color='green', linestyle='--', label=f"Median: ${stats['Median Price']:.2f}")
    ax1.set_xlabel('Price ($)')
    ax1.set_ylabel('Frequency')
    ax1.set_title(f'{symbol} - Price Distribution')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Volume-weighted price distribution
    price_bins = np.linspace(df['price'].min(), df['price'].max(), 30)
    df['price_bin'] = pd.cut(df['price'], bins=price_bins)
    volume_by_price = df.groupby('price_bin')['size'].sum()
    
    ax2.barh(range(len(volume_by_price)), volume_by_price.values, color='coral', alpha=0.7)
    ax2.set_yticks(range(len(volume_by_price)))
    ax2.set_yticklabels([f"${interval.left:.2f}" for interval in volume_by_price.index])
    ax2.set_xlabel('Volume')
    ax2.set_ylabel('Price Range')
    ax2.set_title(f'{symbol} - Volume by Price Level')
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    plt.close(fig)
    
    # Convert stats to DataFrame
    stats_df = pd.DataFrame(list(stats.items()), columns=['Metric', 'Value'])
    
    return {
        'type': 'both',
        'data': stats_df.to_dict('records'),
        'chart': img_str
    }
"""