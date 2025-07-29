import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Database URL from environment variable with default fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://portfolio:secret@localhost:5432/portfolio")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection before using from pool
    pool_size=5,  # Default connection pool size
    max_overflow=10,  # Allow up to 10 connections beyond pool_size
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create a scoped session to ensure thread safety
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

# Base class for all models
Base = declarative_base()


def get_db():
    """Function to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
