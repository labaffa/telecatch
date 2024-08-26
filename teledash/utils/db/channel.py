from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import delete
from teledash.db import models 
from teledash import schemas as schemas
from typing import Union, List, Iterable
from sqlalchemy import func, or_, and_, insert, update
from teledash import config


async def get_channel_by_url(
    db: Session, 
    url: Union[str, None]=None, 
    is_joined: Union[bool, None]=None
):
    filters = []
    if url is not None:
        filters.append(func.lower(models.ChannelCommon.url) == url.lower())

    # TODO: is_joined must be used with ChannelCustom
    # if is_joined is not None:
    #     filters.append(
    #         models.ChannelCommon.is_joined == is_joined
    #     )
    
    query = select(
        models.ChannelCommon.id,
        models.ChannelCommon.access_hash,
        models.ChannelCommon.url,
        models.ChannelCommon.username,
        models.ChannelCommon.type,
        models.ChannelCommon.title,
        models.ChannelCommon.about,
        models.ChannelCommon.messages_count,
        models.ChannelCommon.participants_count,
        models.ChannelCommon.inserted_at,
        models.ChannelCommon.updated_at,
        )\
        .where(*filters)
    raw_result = await db.execute(query)
    result = raw_result.mappings().all()

    if url is not None:
        result = result[0] if result else None
    return result


async def get_channel_common_from_list_of_urls(
    db: Session,
    urls: Iterable[str]
):
    """
    Retrieves channel common information from a list of URLs.

    Args:
        db (Session): The database session.
        urls (Iterable[str]): The list of URLs to retrieve channel information from.

    Returns:
        List[Dict]: A list of dictionaries containing the channel common information.
    """
    if not urls:
        return []
    urls = [url.lower() for url in urls]
    query = select(
        models.ChannelCommon.id,
        models.ChannelCommon.access_hash,
        models.ChannelCommon.url,
        models.ChannelCommon.username,
        models.ChannelCommon.type,
        models.ChannelCommon.title,
        models.ChannelCommon.about,
        models.ChannelCommon.messages_count,
        models.ChannelCommon.participants_count,
        models.ChannelCommon.inserted_at,
        models.ChannelCommon.updated_at,
        )\
        .where(func.lower(models.ChannelCommon.url).in_(urls))
    result = await db.execute(query)
    return result.mappings().all()




async def insert_channel_common(
    db: Session, channel: schemas.ChannelCommon
):
    channel.url = channel.url.lower()  # be sure new channels are lower
    db_channel = models.ChannelCommon(**dict(channel))
    stmt = insert(models.ChannelCommon)\
        .values(**(db_channel.to_dict()))
    await db.execute(stmt)
    await db.commit()
    # await db.refresh(db_channel)
    return db_channel


async def upsert_channel_common(
    db: Session, channel: schemas.ChannelCommon
):
    channel_in_db = await get_channel_by_url(db, channel.url)
    if channel_in_db:
        channel.url = channel_in_db["url"]  # backward compatibility to 'not lower' channels
        stmt = update(models.ChannelCommon)\
            .values(dict(channel))\
            .where(models.ChannelCommon.url == channel.url)
    else:
        channel.url = channel.url.lower()  # new channels are all lowered
        channel_common = models.ChannelCommon(**dict(channel))
        stmt = insert(models.ChannelCommon)\
            .values(channel_common)
    await db.execute(stmt)
    await db.commit()
    # await db.flush()
    return dict(channel)


def upsert_many_channel_common(
    db: Session, channels: List[schemas.ChannelCommon]
):
    # TODO: adapt to case insensitive urls (this function is not used now)
    for channel in channels:
        channel_in_db = get_channel_by_url(db, channel.url)
        if channel_in_db:
            db.query(models.ChannelCommon)\
                .filter_by(url=channel.url)\
                .update(dict(channel))
        else:
            channel_common = models.ChannelCommon(**dict(channel))
            db.add(channel_common)
    db.commit()
    db.flush()
    return [dict(channel) for channel in channels]


def update_messages_count(
    db: Session, channel_url: str, count: Union[int, None]
):
    db.query(models.ChannelCommon)\
        .filter_by(url=channel_url)\
        .update({"messages_count": count})
    db.commit()
    db.flush()


async def update_channel_common(
    db: Session, channel_url: str, update_dict: dict
):
    stmt = update(models.ChannelCommon)\
            .values(dict(update_dict))\
            .where(models.ChannelCommon.url == channel_url)
    
    # db.query(models.ChannelCommon)\
    #     .filter_by(url=channel_url)\
    #     .update(update_dict)
    await db.execute(stmt)
    await db.commit()
    await db.flush()


def insert_single_channel_in_collection(
    db: Session,
    collection_title: str,
    user_id: int,
    channel_url: str
):
    db_channel = models.ChannelCollection(
        user_id=user_id, collection_title=collection_title, channel_url=channel_url
    )
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


async def insert_channel_collection(
    db: Session, 
    collection_title: str,
    user_id: int,
    channels: List[schemas.ChannelCustom] 
):
    db_channels_collection = [
        models.ChannelCollection(
            user_id=user_id, 
            collection_title=collection_title, 
            channel_url=channel.channel_url.lower(),
            language=channel.language,
            location=channel.location,
            category=channel.category

        )
        for channel in channels
    ]
    
    # await db.bulk_save_objects(db_channels_collection)  # db.add_all(db_channels_collection) also ok
    db.add_all(db_channels_collection)
    await db.commit()  # commit at the end of /add_collection ?
    return db_channels_collection


async def get_channel_collection(
    db: Session, 
    user_id: int,
    collection_title: str
):
    filters = [
        models.ChannelCollection.user_id == user_id,
        models.ChannelCollection.collection_title == collection_title
    ]
    query = select(
        models.ChannelCollection.channel_url,
        models.ChannelCommon.url,
        models.ChannelCommon.id,
        models.ChannelCommon.title,
        models.ChannelCommon.username,
        models.ChannelCommon.type,
        models.ChannelCommon.participants_count,
        models.ChannelCommon.messages_count,
        models.ChannelCollection.category,
        models.ChannelCollection.location,
        models.ChannelCollection.language,
        models.ChannelCollection.user_id,
        models.ChannelCollection.collection_title
        )\
        .join(
            models.ChannelCollection,
            func.lower(models.ChannelCommon.url) == func.lower(models.ChannelCollection.channel_url)
        )\
        .where(*filters)
    result = await db.execute(query)
    return result.mappings().all()


async def get_channel_collection_titles_of_user(
    db: Session, user_id: int
):
    filters = [
        models.ChannelCollection.user_id == user_id,
        models.ChannelCollection.collection_title != ""
    ]
    query = select(
        models.ChannelCollection.collection_title
        )\
        .where(*filters)\
        .distinct()
    
    result = await db.execute(query)
    return result.scalars().all()


def get_collection_job(db: Session, uid: str):
    query = select(
        models.CollectionJob.uid,
        models.CollectionJob.user_id,
        models.CollectionJob.collection_title,
        models.CollectionJob.status,
        models.CollectionJob.processed_channels
        )\
        .where(models.CollectionJob.uid == uid)
    result = db.execute(query)
    result = result.mappings().all()
    result = result[0] if result else None
    return result


def upsert_collection_job(db: Session, job: schemas.CollectionJob):
    job_in_db = get_collection_job(db, job.uid)
    if job_in_db:
        db.query(models.CollectionJob)\
            .filter_by(uid=job.uid)\
            .update(dict(job))
    else:
        db_job = models.CollectionJob(**dict(job))
        db.add(db_job)
    db.commit()
    db.flush()
    return job


def get_collection_jobs_of_user(db: Session, user_id: int, status="in_progress"):
    filters = [
        models.CollectionJob.user_id == user_id,
        models.CollectionJob.status == status
    ]
    query = select(
        models.CollectionJob.uid,
        models.CollectionJob.collection_title
        )\
        .where(*filters)
    result = db.execute(query)
    return result.mappings().all()


async def delete_collection_for_user(
    db: Session, 
    collection_title: str,
    user_id: int,
):
    filters = [
        models.ChannelCollection.collection_title == collection_title,
        models.ChannelCollection.user_id == user_id
    ]
    query = delete(
        models.ChannelCollection
        )\
        .where(*filters)
    await db.execute(query)
    await db.commit()


def get_entity_from_db(db: Session, entity_id: int, entity_type: int):
    filters = [
        models.Entity.id == entity_id,
        models.Entity.entity_type == entity_type
    ]
    query = select(
        models.Entity.id,
        models.Entity.entity_type,
        models.Entity.username,
        models.Entity.name,
        models.Entity.phone
        )\
        .where(*filters)
    result = db.execute(query)
    return result.mappings().all()


async def get_entities_in_list(
    db: Session, entities: Iterable[schemas.Entity]
):
    if not entities:
        return []
    conditions = (
        and_(
            models.Entity.id == entity["id"], 
            models.Entity.entity_type == config.EntityType[entity["entity_type"]].value
        ) for entity in entities
    )
    filters = [or_(*conditions)]
    query = select(
        models.Entity.id,
        models.Entity.entity_type,
        models.Entity.username,
        models.Entity.name,
        models.Entity.phone
        )\
        .where(*filters)
    result = await db.execute(query)
    return result.mappings().all()


def insert_entity(
    db: Session, 
    entity: schemas.Entity
):
    db_entity = models.Entity(**dict(entity))
    db.add(db_entity)
    db.commit()
    db.refresh(db_entity)
    return db_entity


async def insert_entities(
    db: Session,
    entities: List[schemas.Entity]
):
    db_entities = [
        models.Entity(**dict(entity)) for entity in entities
    ]
    db.add_all(db_entities)  # it looks non async, I dont know why sqlalchemy suggests it
    # db.bulk_save_objects(db_entities)
    await db.commit()
    return db_entities
    
    