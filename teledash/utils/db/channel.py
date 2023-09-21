from sqlalchemy.orm import Session
from sqlalchemy.future import select
from teledash.db import models 
from teledash import models as schemas
from typing import Union, List, Iterable
from sqlalchemy import func


def get_channel_by_url(
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
        models.ChannelCommon
        )\
        .where(*filters)
    raw_result = db.execute(query)
    result = raw_result.mappings().all()

    if url is not None:
        result = result[0] if result else result
    return result


def get_channels_from_list_of_urls(
    db: Session,
    urls: Iterable[str]
):
    filters = []
    if urls:
        filters.append(models.ChannelCommon.url.in_(urls))
    query = select(
        models.ChannelCommon.username,
        models.ChannelCommon.title,
        models.ChannelCommon.url,
        models.ChannelCommon.type,
        models.ChannelCommon.id,
        models.ChannelCommon.access_hash,
        models.ChannelCommon.participants_count,
        models.ChannelCommon.messages_count,
        models.ChannelCommon.inserted_at,
        models.ChannelCommon.updated_at
        # models.ChannelCustom.location
        )\
        .where(*filters)
        # .join(
        #     models.ChannelCustom,
        #     models.ChannelCommon.id == models.ChannelCustom.channel_id
        # )\
    result = db.execute(query)
    return result.mappings().all()


def get_channels_custom_from_list_of_urls(
    db: Session,
    user_id: int,
    urls: Iterable[str]
):
    filters = [
        models.ChannelCustom.user_id == user_id
    ]
    if urls:
        filters.append(models.ChannelCustom.channel_url.in_(urls))
    query = select(
        models.ChannelCustom.channel_url,
        models.ChannelCustom.category,
        models.ChannelCustom.language,
        models.ChannelCustom.location,
        models.ChannelCustom.is_joined,
        models.ChannelCustom.user_id
        )\
        .where(*filters)
        # .join(
        #     models.ChannelCustom,
        #     models.ChannelCommon.id == models.ChannelCustom.channel_id
        # )\
    result = db.execute(query)
    return result.mappings().all()


def get_channel_custom_by_url(db: Session, url: str, user_id: int):
    query = select(
        models.ChannelCustom
        )\
        .where(
            func.lower(models.ChannelCustom.channel_url) == url.lower(),
            models.ChannelCustom.user_id == user_id
        )
    raw_result = db.execute(query)
    result = raw_result.mappings().all()
    result = result[0] if result else None
    return result


def get_channel_with_custom_fields(
    db: Session, 
    user_id: int,
    url: Union[str, None]=None, 
    is_joined: Union[bool, None]=None
):
    filters = [
        models.ChannelCommon.url == url,
        models.ChannelCustom.user_id == user_id
    ]
    if is_joined is not None:
        filters.append(
            models.ChannelCustom.is_joined == is_joined
        )
    query = select(
        models.ChannelCustom.channel_url,
        models.ChannelCustom.user_id,
        models.ChannelCustom.location,
        models.ChannelCustom.category,
        models.ChannelCustom.language,
        models.ChannelCommon.title,
        models.ChannelCommon.about,
        models.ChannelCommon.id,
        models.ChannelCommon.username
        )\
        .join(
            models.ChannelCustom, 
            models.ChannelCommon.url == models.ChannelCustom.channel_url)\
        .where(*filters)
    result = db.execute(query)
    return result.mappings().all()


def insert_channel_common(
    db: Session, channel: schemas.ChannelCommon
):
    db_channel = models.ChannelCommon(**dict(channel))
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


def upsert_channel_common(
    db: Session, channel: schemas.ChannelCommon
):
    channel_in_db = get_channel_by_url(db, channel.url)
    if channel_in_db:
        channel.url = channel_in_db["url"]  # backward compatibility to 'not lower' channels
        db.query(models.ChannelCommon)\
            .filter_by(url=channel.url)\
            .update(dict(channel))
    else:
        channel.url = channel.url.lower()  # new channels are all lowered
        channel_common = models.ChannelCommon(**dict(channel))
        db.add(channel_common)
    db.commit()
    db.flush()
    return dict(channel)


def upsert_many_channel_common(
    db: Session, channels: List[schemas.ChannelCommon]
):
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


def update_channel_common(
    db: Session, channel_url: str, update_dict: dict
):
    
    db.query(models.ChannelCommon)\
        .filter_by(url=channel_url)\
        .update(update_dict)
    db.commit()
    db.flush()


def insert_channel_custom(
    db: Session, channel: schemas.ChannelCustom
):
    db_channel = models.ChannelCustom(**dict(channel))
    db.add(db_channel)
    db.commit()
    db.refresh(db_channel)
    return db_channel


def upsert_channel_custom(
    db: Session, channel: schemas.ChannelCustom      
):
    # channel.channel_url = channel.channel_url.lower()
    channel_in_db = get_channel_custom_by_url(db, channel.channel_url, channel.user_id)
    
    if channel_in_db:
        # this is due to 'select(ChannelCustom)' in query. TODO: fix this
        channel_in_db = next(v.to_dict() for k, v in channel_in_db.items())

        channel.channel_url = channel_in_db["channel_url"]  # to not remove not lowered ones
        db.query(models.ChannelCustom)\
            .filter_by(channel_url=channel_in_db["channel_url"])\
            .update(dict(channel))
    else:
        channel.channel_url = channel.channel_url.lower()  # new channels will be lower 
        channel_custom = models.ChannelCustom(**dict(channel))
        db.add(channel_custom)
    db.commit()
    db.flush()
    return dict(channel)


def upsert_many_channel_custom(
    db: Session, channels: List[dict]
):
    for channel in channels:
        channel_in_db = get_channel_custom_by_url(
            db, channel["channel_url"], channel["user_id"]
        )
        if channel_in_db:
            db.query(models.ChannelCustom)\
                .filter_by(channel_url=channel["channel_url"])\
                .update(dict(channel))
        else:
            channel_custom = models.ChannelCustom(**dict(channel))
            db.add(channel_custom)
    db.commit()
    db.flush()
    return {"status": "ok"}


def update_channel_custom(
    db: Session, channel_url: str, user_id: int, update_dict: dict
):
    # _, _ = update_dict.pop("channel_id"), update_dict.pop("user_id")

    # common_channel = select(
    #     models.ChannelCommon.id
    #     )\
    #     .where(models.ChannelCommon.url == channel_url)
    db.query(models.ChannelCustom).\
        filter(
            models.ChannelCustom.channel_url == channel_url,
            models.ChannelCustom.user_id == user_id
        )\
        .update(update_dict)
    db.commit()
    db.flush()


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


def insert_channel_collection(
    db: Session, 
    collection_title: str,
    user_id: int,
    channels: List[schemas.ChannelCreate] 
):
    db_channels_collection = [
        models.ChannelCollection(
            user_id=user_id, collection_title=collection_title, channel_url=channel.url.lower()
        )
        for channel in channels
    ]
    
    db.bulk_save_objects(db_channels_collection)  # db.add_all(db_channels_collection) also ok
    db.commit()
    return db_channels_collection


def get_channel_collection(
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
        models.ChannelCommon.title,
        models.ChannelCommon.username,
        models.ChannelCommon.type,
        models.ChannelCommon.participants_count,
        models.ChannelCommon.messages_count,
        models.ChannelCustom.category,
        models.ChannelCustom.location,
        models.ChannelCustom.language
        )\
        .join(
            models.ChannelCollection,
            func.lower(models.ChannelCommon.url) == func.lower(models.ChannelCollection.channel_url)
        )\
        .join(
            models.ChannelCustom,
            func.lower(models.ChannelCustom.channel_url) == func.lower(models.ChannelCollection.channel_url)
        )\
        .where(*filters)
    result = db.execute(query)
    return result.mappings().all()


def get_channel_collection_titles_of_user(
    db: Session, user_id: int
):
    filters = [
        models.ChannelCollection.user_id == user_id
    ]
    query = select(
        models.ChannelCollection.collection_title
        )\
        .where(*filters)\
        .distinct()
    
    result = db.execute(query)
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