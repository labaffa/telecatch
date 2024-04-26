from teledash import schemas
from fastapi import APIRouter, HTTPException, Depends, Request, \
    Query, UploadFile
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import base64
from typing import Union, List, Dict
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.utils.db import channel as uc
from teledash.utils import telegram
from teledash import schemas
from uuid import UUID
from teledash.db import models as db_models
from teledash.utils.db import user as uu
from teledash.utils.users import active_user
from teledash.utils import channels as util_channels
import pandas as pd
import numpy as np
import io


channel_router = APIRouter()
jobs: Dict[UUID, schemas.Job] = {}


@channel_router.get("/api/get_channel")
async def read_get_channel(
    request: Request,
    channel: Union[str, int],
    client_id: str,
    db: Session = Depends(get_async_session)
):
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(db, client_id)
        if tg_client is None:
            raise HTTPException(status_code=400, detail="Client is not usable. Register it")
        request.app.state.clients[client_id] = tg_client
    response = await util_channels.get_channel_or_megagroup(tg_client, channel)
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))


@channel_router.get("/channels_info")
async def info_of_channels_and_groups(
    db: Session = Depends(get_async_session),
    channel_urls: List[str]=Query(default=[]),
    user: db_models.User = Depends(active_user)
):
    # sql_result = uc.get_channel_by_url(db=db, is_joined=is_joined)
    

    # # TODO: understand why sql_result output is different from
    # # fewsboard one. 
    # channels = [row[0].to_dict() for row in sql_result]

    # the if-else is used here because uc function gets all the channels  
    # present in the DB if channel_urls is empty (should I modify this behavior?)
    if channel_urls:
        channels = await uc.get_channels_from_list_of_urls(db, channel_urls, user.id)
    else:
        channels = []
    meta = {
        "channel_count": sum(
            1 for c in channels if c["type"] == "channel"),
        "group_count": sum(
            1 for c in channels if c["type"] != "channel"),
        "participant_count": sum(
            int(c["participants_count"]) 
            for c in channels if c["participants_count"]),
        "msg_count": sum(
            int(c["messages_count"]) 
            for c in channels if c["messages_count"])
    }
    data = [schemas.ChannelInfo(**c) for c in channels]
    return {"meta": meta, "data": data}


@channel_router.get("/channels_custom_info")
async def info_of_channels_custom(
    db: Session = Depends(get_async_session),
    channel_urls: List[str]=Query(default=[]),
    user = Depends(active_user)
):
    channels = await uc.get_channels_custom_from_list_of_urls(db, user.id, channel_urls)
    data = [schemas.ChannelCustom(**c) for c in channels]
    return data


# @channel_router.post(
#     "/api/channel", 
#     response_model=schemas.ChannelCommon
# )
# async def add_channel(
#     request: Request,
#     channel: schemas.ChannelCreate,
#     client_id: str,
#     db: Session = Depends(get_async_session)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(db, client_id)
#         request.app.state.clients[client_id] = tg_client
#     channel_in_db = await uc.get_channel_by_url(db, channel.url)
#     record = None
#     if channel_in_db:
#         return channel_in_db
#     try:
#         record = await telegram.build_chat_info(
#             tg_client, channel.url
#         )
        
#         uc.insert_channel_common(db, record)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return record


# @channel_router.delete(
#     "/api/channel_common", 
#     # response_model=models.Channel
# )
# async def delete_channel_common_from_db(
#     channel: models.ChannelCreate,
#     db: Session = Depends(get_db)
# ):
#     channel_in_db = uc.get_channel_by_url(db, channel.url)
    
#     if not channel_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail="Channel is not present in the database"
#         )
#     # if (not channel_in_db) or (not channel_in_db["is_joined"]):
#     #     raise HTTPException(
#     #         status_code=400, detail="Channel is not registered"
#     #     )
    
#     # input_entity_info = {
#     #     "id": int(channel_in_db["id"]),
#     #     "access_hash": channel_in_db["access_hash"]
#     # }
#     # await leave_channel(tg_client, input_entity_info)
#     # left_channel = channels.search(
#     #     Ch.identifier == channel.identifier
#     # )[0]
#     try:
#         stmt = delete(db_models.ChannelCommon)\
#             .where(db_models.ChannelCommon.url == channel.url)
#         db.execute(stmt)
#         db.commit()
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return {
#         "status": "ok", "data": channel_in_db
#     }


# @channel_router.delete(
#     "/api/channel_custom", 
#     # response_model=models.Channel
# )
# async def delete_channel_custom_from_db(
#     channel: models.ChannelCreate,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     channel_in_db = uc.get_channel_custom_by_url(db, channel.url, user.id)
    
#     if not channel_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail="Channel is not present in your account's channels"
#         )
#     try:
#         stmt = delete(db_models.ChannelCustom)\
#             .where(
#                 db_models.ChannelCustom.channel_url == channel.url,
#                 db_models.ChannelCustom.user_id == user.id
#             )
#         db.execute(stmt)
#         db.commit()
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return {
#         "status": "ok", "data": channel_in_db
#     }



# @channel_router.put("/api/chat_message_count")
# async def update_number_of_messages_in_chat(
#     request: Request,
#     channel: models.ChannelCreate,
#     client_id: str,
#     db: Session = Depends(get_db)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
#     channel_in_db = uc.get_channel_by_url(db, channel.url)  # returns dict or None

#     if not channel_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail="Channel is not in db. See /api/channel"
#         )
#     input_entity_info = {
#         "id": channel_in_db.get("id"),
#         "access_hash": int(channel_in_db.get("access_hash"))
#     }
#     msg_count = await count_peer_messages(
#         tg_client, input_entity_info
#     )
#     uc.update_messages_count(
#         db, channel_in_db.get("url"), int(msg_count["msg_count"])
#     )
#     response = uc.get_channel_by_url(db, channel.url)
#     return JSONResponse(content=jsonable_encoder(
#         response, custom_encoder={
#         bytes: lambda v: base64.b64encode(v).decode('utf-8')})
#     )


# @channel_router.put("/api/chat_participant_count")
# async def update_number_of_participants_in_chat(
#     request: Request,
#     channel: models.ChannelCreate,
#     client_id: str,
#     db: Session = Depends(get_db)
# ):
    
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
#     channel_in_db = uc.get_channel_by_url(db, channel.url)
#     if not channel_in_db:
#         raise HTTPException(
#             status_code=400,
#             detail="Channel is not in db. See /api/channel"
#         )
#     input_entity_info = {
#         "id": int(channel_in_db.get("id")),
#         "access_hash": int(channel_in_db.get("access_hash"))
#     }
#     info = await get_channel_or_megagroup(
#         tg_client, input_entity_info
#     )
#     pts_count = info["full_chat"]["participants_count"]
#     uc.update_channel_common(
#         db, channel_in_db.get("url"), {"participants_count": pts_count}
#     )
#     response = uc.get_channel_by_url(db, channel.url)
#     return JSONResponse(content=jsonable_encoder(
#         response, custom_encoder={
#         bytes: lambda v: base64.b64encode(v).decode('utf-8')})
#     )


# @channel_router.put(
#     "/api/update_chat",
#     response_model=models.ChannelCommon
# )
# async def update_dynamic_variables_of_a_chat(
#     request: Request,
#     channel: models.ChannelCreate,
#     client_id: str,
#     db: Session = Depends(get_db)
# ):  
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
#     channel_in_db = uc.get_channel_by_url(db, channel.url)
#     if not channel_in_db:
#         raise HTTPException(
#             status_code=400,
#             detail="Channel is not in db. See /api/channel"
#         )
#     input_entity_info = {
#         "id": int(channel_in_db.get("id")),
#         "access_hash": int(channel_in_db.get("access_hash"))
#     }
#     chat_info = await get_channel_or_megagroup(
#         tg_client, input_entity_info
#     )
#     msg_count = await count_peer_messages(
#         tg_client, input_entity_info
#     )
#     pts_count = chat_info["full_chat"]["participants_count"]
#     uc.update_channel_common(
#         db,
#         channel_in_db.get("url"),
#         {
#             "messages_count": msg_count["msg_count"],
#             "participants_count": pts_count
#         }
#     )
#     response = uc.get_channel_by_url(db, channel.url)
#     return JSONResponse(content=jsonable_encoder(
#         response, custom_encoder={
#         bytes: lambda v: base64.b64encode(v).decode('utf-8')})
#     )


# @channel_router.post(
#     "/api/list_of_channels", 
#     # response_model=models.ChannelCommon
# )
# async def add_list_of_channels(
#     request: Request,
#     channels: List[models.ChannelCreate],
#     client_id: str,
#     db: Session = Depends(get_db)
# ):
#     response = []
#     for channel in channels:
        
#         record = {"url": channel.url, "error": None}
#         try:
#             await add_channel(
#                 request=request, channel=channel, client_id=client_id, db=db
#             )
#             record["status"] = "ok"
#             time.sleep(1)
#         except Exception as e:
#             record["error"] = str(e)
#             record["status"] = "fail"
#         response.append(record)
#     return response


# @channel_router.websocket(
#     "/api/list_of_channels_ws", 
#     # response_model=models.ChannelCommon
# )
# async def add_list_of_channels_ws(
#     websocket: WebSocket,
#     client_id: str,
#     channels: List[str]=Query(default=[]),
#     db: Session = Depends(get_db)
# ):
#     await websocket.accept()
#     response = []
#     for i, channel in enumerate(channels):
#         record = {"url": channel, "error": None, "index": i + 1, "n_channels": len(channels)}
#         try:
#             await add_channel(
#                 request=websocket, channel=models.ChannelCreate(url=channel), 
#                 client_id=client_id, db=db
#             )
#             record["status"] = "ok"
#             time.sleep(1)
#         except Exception as e:
#             record["error"] = str(e)
#             record["status"] = "fail"
#         await websocket.send_json(record)
#         response.append(record)
#     return response


# async def process_channels(
#     task_id: UUID, 
#     channels: List[str],
#     request: Request, 
#     collection_title: str, 
#     client_id: str, 
#     user_id: int,
#     db: Session
# ):
#     processed_channels = []
#     job = schemas.CollectionJob(
#         uid=task_id, status="in_progress", 
#         processed_channels='[]', collection_title=collection_title, user_id=user_id
#     )
#     for i, channel in enumerate(channels):
#         await asyncio.sleep(10)  # pretend long task
#         record = {"url": channel, "error": None, "index": i+1, "n_channels": len(channels)}
#         try:
#             await add_channel(
#                 request=request, channel=models.ChannelCreate(url=channel), 
#                 client_id=client_id, db=db
#             )
#             uc.insert_single_channel_in_collection(
#                 db, collection_title, user_id, channel
#             )
#             record["status"] = "ok"
#             await asyncio.sleep(1)
#         except Exception as e:
#             record["error"] = str(e)
#             record["status"] = "fail"
            
#         processed_channels.append(record)
#         serialized_processed_channels = json.dumps(processed_channels)
#         job.processed_channels = serialized_processed_channels
#         uc.upsert_collection_job(db, job)
#         # jobs[task_id].processed_channels.append(record)
#     job.status = "completed"
#     uc.upsert_collection_job(db, job)
#     # jobs[task_id].status = "completed"


# @channel_router.post(
#     "/api/channels_collection_background", 
#     status_code=202
#     # response_model=models.ChannelCommon
# )
# async def add_channels_collection_in_background(
#     request: Request,
#     background_tasks: BackgroundTasks,
#     channels: List[str],
#     collection_title: str,
#     client_id: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     try:
#         tg_client = request.app.state.clients.get(client_id)
#         if tg_client is None:
#             tg_client = await telegram.get_authenticated_client(client_id)
#             request.app.state.clients[client_id] = tg_client
#     except Exception:
#         raise HTTPException(
#             status_code=400,
#             detail="No Telegram client registered or connection problems"
#         )
#     collection_in_db = uc.get_channel_collection(db, user.id, collection_title)
#     if collection_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Title '{collection_title}' already present in your collections"
#         )
#     new_task_uid = str(uuid4())
#     new_task = models.CollectionJob(
#         uid=new_task_uid, user_id=user.id, collection_title=collection_title
#     )
#     background_tasks.add_task(
#         process_channels,
#         new_task.uid,
#         channels,
#         request,
#         collection_title,
#         client_id,
#         user.id,
#         db
#     )
#     uc.upsert_collection_job(db, new_task)
#     # jobs[new_task.uid] = new_task
#     return new_task


# @channel_router.get("/api/work/{uid}/status")
# async def status_handler(uid: UUID, db: Session=Depends(get_db)):
#     sql_result = uc.get_collection_job(db, str(uid))
#     if not sql_result:
#         raise HTTPException(
#             status_code=400,
#             detail=f"No job found with uid {uid}"
#         )
#     return schemas.CollectionJob(**sql_result)


# @channel_router.get("/api/collection_jobs_of_user")
# async def get_collection_jobs_of_user(
#     user=Depends(config.settings.MANAGER),
#     db: Session=Depends(get_db)
# ):
#     try:
#         return uc.get_collection_jobs_of_user(db, user.id)
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail=str(e)
#         )


# @channel_router.post("/api/channel_custom")
# async def add_custom_channel_fields_from_user(
#     request: Request,
#     channel_custom: dict,
#     client_id: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
#     record = channel_custom    
#     try:
#         record["user_id"] = user.id
#         uc.insert_channel_custom(db, schemas.ChannelCustom(**record))
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return record


# @channel_router.post("/api/list_of_channels_custom")
# async def add_list_of_channels_custom(
#     request: Request,
#     channels_custom: List[dict],
#     client_id: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     response = []
#     for channel in channels_custom:
#         record = {"data": channel, "error": None}
#         try:
#             await add_custom_channel_fields_from_user(
#                 request=request, channel_custom=channel, client_id=client_id, db=db, user=user
#             )
#             record["status"] = "ok"
#         except Exception as e:
#             record["error"] = str(e)
#             record["status"] = "fail"
#         response.append(record)
#     return response


# @channel_router.put("/api/update_channel_custom")
# async def update_custom_channel_fields_from_user(
#     request: Request,
#     channel_url: str,
#     update_dict: dict,
#     client_id: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
    
#     try:
#         uc.update_channel_custom(db, channel_url, user.id, update_dict)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     record = uc.get_channel_with_custom_fields(db, user.id, channel_url)
    
#     return {
#         "status": "ok", 
#         "data": record
#     }


# @channel_router.post("/api/channel_collection")
# async def add_collection_item_for_user(
#     request: Request,
#     collection: models.ChannelCollectionPayload,
#     client_id: str,
#     db: Session = Depends(get_async_session),
#     user = Depends(active_user)
# ):
#     tg_client = request.app.state.clients.get(client_id)
#     if tg_client is None:
#         tg_client = await telegram.get_authenticated_client(client_id)
#         request.app.state.clients[client_id] = tg_client
#     collection_in_db = uc.get_channel_collection(db, user.id, collection.collection_title)
#     if collection_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Title '{collection.collection_title}' already present in your collections")
#     try:
#         channel_urls = list(set(collection.channel_urls))
#         uc.insert_channel_collection(
#             db, collection.collection_title, user.id, channel_urls
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     record = uc.get_channel_collection(db, user.id, collection.collection_title)
#     return {
#         "status": "ok",
#         "data": record
#     }


@channel_router.post("/add_collection")
async def add_collection_of_channels_to_user_account(
    request: Request,
    collection_title: str,
    file: UploadFile,
    db: Session = Depends(get_async_session),
    user: schemas.User =  Depends(active_user)
):
    content = await file.read()
    file_channels = []
    try:
        # Try parsing as CSV
        df = pd.read_csv(
            io.BytesIO(content), 
            sep=None, 
            engine="python",
            encoding="ISO-8859-1"
            
        )
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
            )
    # TODO: check if columns don't match schema
    if len(df) == 0:
        raise HTTPException(
            status_code=400, 
            detail=f"List of channels for the collection '{collection_title}' is empty"
        )
    try:
        df.columns = df.columns.str.lower()
        df = df.replace({np.nan: None})
        if "url" in df.columns:
            df.rename(columns={"url": "channel_url"}, inplace=True)
        df = df.drop_duplicates("channel_url")
        for row in df.to_dict("records"):
            row_d = schemas.ChannelCustomCreate(**dict(row)).model_dump()
            file_channels.append(row_d)
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=str(e)
        )
    
    client_id = await uu.get_active_client(db, user.id)
    tg_client = request.app.state.clients.get(client_id)
    if tg_client is None:
        tg_client = await telegram.get_authenticated_client(db, client_id)
        request.app.state.clients[client_id] = tg_client
    collection_in_db = await uc.get_channel_collection(
        db, user.id, collection_title)
    if collection_in_db:
        raise HTTPException(
            status_code=400, 
            detail=f"Title '{collection_title}' already present in your collections"
        )
    try:
        for channel in file_channels:
            channel_url = channel["channel_url"]
            channel_common_in_db = await uc.get_channel_by_url(
                db, channel_url
            )
            if not channel_common_in_db:
                channel_common = schemas.ChannelCommon(url=channel_url.lower())
                await uc.insert_channel_common(db, channel_common)
            
            channel_custom = schemas.ChannelCustom(**dict(channel), user_id=user.id)
            await uc.upsert_channel_custom(db, channel_custom)
        await uc.insert_channel_collection(
            db, 
            collection_title, user.id, 
            [schemas.ChannelCreate(url=x["channel_url"]) for x in file_channels]
        )
        record = await uc.get_channel_collection(db, user.id, collection_title)
        response = {
            "status": "ok",
            "data": record
        }
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @channel_router.delete("/api/channel_collection")
# async def delete_collection_item_for_user(
#     collection_title: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     collection_in_db = uc.get_channel_collection(db, user.id, collection_title)
#     if not collection_in_db:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Title '{collection_title}' is not present in your collections")
#     try:
#         uc.delete_collection_for_user(db, collection_title, user.id)
        
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return {
#         "status": "ok",
#         "data": collection_in_db
#     }


# @channel_router.get("/api/channel_collections_of_user")
# async def get_collections_registered_by_an_user(
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     try:
#         response = uc.get_channel_collection_titles_of_user(db, user.id)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return {
#         "status": "ok",
#         "data": response
#     }


# @channel_router.get("/api/channel_collection_by_title")
# async def get_channels_of_a_given_collection_title(
#     collection_title: str,
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     try:
#         response = uc.get_channel_collection(db, user.id, collection_title)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     return {
#         "status": "ok",
#         "data": response
#     }


# @channel_router.post("/api/init_many_channels_to_db")
# async def upsert_many_channels_to_common_and_custom_tables(
#     channels: List[schemas.ChannelCustomCreate],
#     db: Session = Depends(get_async_session),
#     user = Depends(active_user)
# ):
#     try:
#         for channel in channels:
#             channel_common_in_db = uc.get_channel_by_url(
#                 db, channel.channel_url
#             )
#             if not channel_common_in_db:
#                 channel_common = schemas.ChannelCommon(url=channel.channel_url.lower())
#                 uc.insert_channel_common(db, channel_common)
            
#             channel_custom = schemas.ChannelCustom(**dict(channel), user_id=user.id)
#             uc.upsert_channel_custom(db, channel_custom)
#     except Exception as e:
#         raise HTTPException(
#             status_code=400, detail=str(e)
#         )
#     return {
#         "status": "ok",
#         # "data": {"customs": customs, "commons": commons}
#     }


# @channel_router.get("/api/get_entity")
# async def get_entity(
#     request: Request,
#     entity_input: Union[str, int], 
#     db: Session = Depends(get_db),
#     user = Depends(config.settings.MANAGER)
# ):
#     try:
#         entity_input = int(entity_input)
#     except Exception:
#         pass
#     try:
#         client_id = uu.get_active_client(db, user.id)
#         tg_client = request.app.state.clients.get(client_id)
#         if tg_client is None:
#             tg_client = await telegram.get_authenticated_client(client_id)
#             request.app.state.clients[client_id] = tg_client
#         entity = await tg_client.get_entity(entity_input)
#         entity = entity.to_dict()
#         entity.pop("photo")  # photo contains bytes and need to be utf8 encoded
#     except Exception as e:
#         raise HTTPException(
#             status_code=400, detail=str(e)
#         )
#     return entity
    
