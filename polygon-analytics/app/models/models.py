from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, BigInteger, Index
from sqlalchemy.sql import func
from app.models.database import Base
from datetime import datetime

class TickData(Base):
    __tablename__ = "tick_data"
    
    id = Column(BigInteger, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    size = Column(Integer, nullable=False)
    exchange = Column(String(10))
    conditions = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )

class AnalyticsTemplate(Base):
    __tablename__ = "analytics_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    prompt = Column(Text, nullable=False)
    python_code = Column(Text, nullable=False)
    output_type = Column(String(50))  # 'table', 'chart', 'both'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
class QueryHistory(Base):
    __tablename__ = "query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    template_id = Column(Integer)
    result = Column(JSON)
    execution_time = Column(Float)
    created_at = Column(DateTime, default=func.now())