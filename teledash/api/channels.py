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
from teledash.utils.admin import enc_key_from_cookies


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
        enc_key = enc_key_from_cookies(request)
        tg_client = await telegram.get_authenticated_client(db, client_id, enc_key)
        if tg_client is None:
            raise HTTPException(status_code=400, detail="Client is not usable. Register it")
        request.app.state.clients[client_id] = tg_client
    response = await util_channels.get_channel_or_megagroup(tg_client, channel)
    return JSONResponse(content=jsonable_encoder(
        response, custom_encoder={
        bytes: lambda v: base64.b64encode(v).decode('utf-8')}))


@channel_router.get("/info_of_channels_in_collection")
async def info_of_channels_in_collection(

    db: Session = Depends(get_async_session),
    collection_title: str=Query(default=""),
    user: db_models.User = Depends(active_user)
):
    channels = await uc.get_channel_collection(db, user.id, collection_title)
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



