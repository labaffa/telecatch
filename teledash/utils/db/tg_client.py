from sqlalchemy.orm import Session
from sqlalchemy import select, update, insert
# from sqlalchemy.future import select, update, insert
from teledash.db import models 
from teledash import schemas as schemas
from typing import Union


async def get_clients_meta(db: Session):
    query = select(models.TgClient)
    result = await db.execute(query)
    return result.fetchall()


async def get_client_meta(db: Session, client_id: str):
    query = select(
        models.TgClient
        )\
        .where(models.TgClient.id == client_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_clients(
    db: Session, user: models.User
):
    query = select(
        models.UserClient.client_id,
        models.TgClient.phone,
        models.TgClient.authenticated
        )\
        .join(
            models.TgClient, 
            models.UserClient.client_id == models.TgClient.id)\
        .where(models.UserClient.user_id == user.id)
    result = await db.execute(query)
    return result.mappings().all()


async def user_client_exist(db: Session, user_id: int, client_id: str):
    query = select(
        models.UserClient
        )\
        .where(
            models.UserClient.user_id == user_id,
            models.UserClient.client_id == client_id
        )
    result = await db.execute(query)
    result = result.scalar_one_or_none()
    if result:
        return True
    else:
        return False
    

async def upsert_user_client_relation(
    db: Session, user_id: int, client_id: str
):  
    client_exists = await user_client_exist(db, user_id, client_id)
    if client_exists:
        return
    # user_client = models.UserClient(
    #     user_id=user_id, client_id=client_id
    # )
    user_client = {"user_id": user_id, "client_id": client_id}
    stmt = insert(models.UserClient).values(**user_client)
    # db.add(user_client)
    await db.execute(stmt)
    await db.commit()
    # await db.refresh(user_client)
    return user_client


async def upsert_tg_client(
    db: Session, row_dict: dict
):
    """this SHOULD NOT be implemented this way, but 
    rather in one sql statement/operation (using dialects)
    """
    client_meta = await get_client_meta(db, row_dict["id"])
    if client_meta:
        print("client_meta")
        query = update(models.TgClient)\
            .values(**row_dict)\
            .where(models.TgClient.id == row_dict["id"])
        # db.query(models.TgClient)\
        #     .filter_by(id=row_dict["id"])\
        #     .update(row_dict)
    else:
        print("not client_meta")
        tg_client = models.TgClient(**row_dict)
        # db.add(tg_client)
        query = insert(models.TgClient).values(row_dict)
    await db.execute(query)
    await db.commit()
    await db.flush()
    print("inserted")
    return row_dict


