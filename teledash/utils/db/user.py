from sqlalchemy.orm import Session
from sqlalchemy.future import select
from teledash.db import models 
from teledash import models as schemas


def get_user(db: Session, user_id: int):
    query = select(models.User)\
        .where(models.User.id == user_id)
    result = db.execute(query)
    return result.scalar_one_or_none()


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
        
    
def get_active_collection(db: Session, user_id: int):
    query = select(models.ActiveCollection.collection_title)\
        .where(models.ActiveCollection.user_id == user_id)
    result = db.execute(query)
    return result.scalar_one_or_none()


def upsert_active_collection(db: Session, user_id: int, collection_title: str):
    active_collection_in_db = get_active_collection(db, user_id)
    if active_collection_in_db:
        db.query(models.ActiveCollection)\
            .filter_by(user_id=user_id)\
            .update({"collection_title": collection_title})
    else:
        db.add(models.ActiveCollection(
                user_id=user_id, collection_title=collection_title
        ))
    db.commit()
    db.flush()
     





