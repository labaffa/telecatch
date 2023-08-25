from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from teledash import config
import os


SQLALCHEMY_DATABASE_URL = (
    'sqlite:///' + 
    + '{os.path.join(config.SESSIONS_FOLDER, "teledash.db")}'
)
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


async def get_db():
    async with SessionLocal() as db:
        yield db
        await db.commit()