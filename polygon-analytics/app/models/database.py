from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# Optimize database connection with connection pooling and performance settings
engine = create_engine(
    settings.database_url,
    pool_size=20,  # Increased pool size for concurrent operations
    max_overflow=40,  # Allow more connections when needed
    pool_pre_ping=True,  # Check connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False,  # Disable SQL logging for performance
    connect_args={
        "options": "-c statement_timeout=300000"  # 5 minute timeout
    }
)

# Optimize session settings
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False,  # Don't auto-flush for better batch performance
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()