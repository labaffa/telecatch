from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import update, insert
from teledash.db import models 
from teledash import schemas as schemas


def get_user(db: Session, user_id: int):
    query = select(models.User)\
        .where(models.User.id == user_id)
    result = db.execute(query)
    return result.scalar_one_or_none()


def get_all_usernames(db: Session):
    query = select(models.User.username)
    result = db.execute(query)
    return result.mappings().all()


def get_user_by_email(db: Session, email: str):
    query = select(models.User)\
        .where(models.User.email == email)
    result = db.execute(query)
    return result.scalar_one_or_none()


def get_user_by_username(db: Session, username: str):
    query = select(models.User)\
        .where(models.User.username == username)
    result = db.execute(query)
    return result.scalar_one_or_none()


def create_user(db: Session, user: schemas.UserInDB):
    db_user = models.User(**user)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_all_channel_urls(db: Session, user_id: int):
    query = select(
        models.ChannelCustom.channel_url.label("url")
        )\
        .where(models.ChannelCustom.user_id == user_id)
    raw_result = db.execute(query)
    return raw_result.mappings().all()
        
    
async def get_active_collection(db: Session, user_id: int):
    query = select(models.ActiveCollection.collection_title)\
        .where(
            models.ActiveCollection.user_id == user_id,
            models.ActiveCollection.collection_title != "" # empty collections are not allowed
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def upsert_active_collection(db: Session, user_id: int, collection_title: str):
    active_collection_in_db = await get_active_collection(db, user_id)
    if active_collection_in_db is not None:  # get_active_collection returns scalar or None
        stmt = update(models.ActiveCollection)\
            .values({"collection_title": collection_title})\
            .where(
                models.ActiveCollection.user_id == user_id,
                models.ActiveCollection.collection_title != ""
            )        
        # db.query(models.ActiveCollection)\
        #     .filter(
        #         models.ActiveCollection.user_id == user_id,
        #         models.ActiveCollection.collection_title != ""
        #     )\
        #     .update({"collection_title": collection_title})
    else:
        stmt = insert(models.ActiveCollection)\
            .values(user_id=user_id, collection_title=collection_title)
        # db.add(models.ActiveCollection(
        #         user_id=user_id, collection_title=collection_title
        # ))
    await db.execute(stmt)
    await db.commit()
    await db.flush()


async def get_active_client(db: Session, user_id: int):
    query = select(
        models.ActiveClient.client_id)\
        .where(
            models.ActiveClient.user_id == user_id
        )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def upsert_active_client(db: Session, user_id: int, client_id: str):
    active_client_in_db = await get_active_client(db, user_id)
    if active_client_in_db is not None:
        stmt = update(models.ActiveClient)\
            .values(client_id=client_id)\
            .where(models.ActiveClient.user_id == user_id)
        # db.query(models.ActiveClient)\
        #     .filter(models.ActiveClient.user_id == user_id)\
        #     .update({"client_id": client_id})
    else:
        stmt = insert(models.ActiveClient)\
            .values({"user_id": user_id, "client_id": client_id})
        # 
    await db.execute(stmt)
    await db.commit()
    await db.flush()






