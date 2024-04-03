from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from teledash import config
import os



engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(
    engine, 
    expire_on_commit=False, 
    autocommit=False, 
    autoflush=False
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()