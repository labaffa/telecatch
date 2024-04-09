from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from teledash.config import SQLALCHEMY_DATABASE_URL
from teledash.db.models import User
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi import Depends
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine



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

a_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True
    )
async_session_maker = async_sessionmaker(
    a_engine, expire_on_commit=False, autocommit=False, autoflush=False, 
    class_=AsyncSession
)


class Base(DeclarativeBase):
    pass

# Base = declarative_base()

async def create_db_and_tables():
    async with a_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_user_db(session: Session = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)