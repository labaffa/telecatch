from sqlalchemy.orm import Session
from sqlalchemy.future import select
from teledash.db import models 
from teledash import models as schemas
from typing import Union


def get_clients_meta(db: Session):
    query = select(models.TgClient)
    result = db.execute(query)
    return result.fetchall()


def get_client_meta(db: Session, client_id: str):
    query = select(
        models.TgClient
        )\
        .where(models.TgClient.id == client_id)
    result = db.execute(query)
    return result.scalar_one_or_none()


def get_user_clients(
    db: Session, user_id: int
):
    query = select(
        models.UserClient.client_id,
        models.TgClient.phone,
        models.TgClient.authenticated
        )\
        .join(
            models.TgClient, 
            models.UserClient.client_id == models.TgClient.id)\
        .where(models.UserClient.user_id == user_id)
    result = db.execute(query)
    return result.mappings().all()


def user_client_exist(db: Session, user_id: int, client_id: str):
    query = select(
        models.UserClient
        )\
        .where(
            models.UserClient.user_id == user_id,
            models.UserClient.client_id == client_id
        )
    result = db.execute(query)
    result = result.scalar_one_or_none()
    if result:
        return True
    else:
        return False
    

def upsert_user_client_relation(
    db: Session, user_id: int, client_id: str
):  
    if user_client_exist(db, user_id, client_id):
        return
    user_client = models.UserClient(
        user_id=user_id, client_id=client_id
    )
    db.add(user_client)
    db.commit()
    db.refresh(user_client)
    return user_client


def upsert_tg_client(
    db: Session, row_dict: dict
):
    """this SHOULD NOT be implemented this way, but 
    rather in one sql statement/operation (using dialects)
    """
    client_meta = get_client_meta(db, row_dict["id"])
    if client_meta:
        db.query(models.TgClient)\
            .filter_by(id=row_dict["id"])\
            .update(row_dict)
    else:
        tg_client = models.TgClient(**row_dict)
        db.add(tg_client)
    db.commit()
    db.flush()
    return row_dict


