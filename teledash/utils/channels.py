from teledash import schemas
from teledash.utils import telegram as ut
from teledash.utils.db import channel as uc
import hashlib
from typing import Union
from telethon import functions, types
from sqlalchemy.orm import Session
import datetime as dt
import asyncio


def create_session_id(api_phone, api_id, api_hash):
    """
    Generate a filename for the session file

    This is a combination of phone number and API credentials, but hashed
    so that one cannot actually derive someone's phone number from it.

    :param str api_phone:  Phone number for API ID
    :param int api_id:  Telegram API ID
    :param str api_hash:  Telegram API Hash
    :return str: A hash value derived from the input
    """
    hash_base = api_phone.strip().replace("+", "") + str(api_id).strip() + api_hash.strip()
    return hashlib.blake2b(hash_base.encode("ascii")).hexdigest()


async def get_input_entity(client, channel_info):
    try:
        channel_id = int(channel_info["id"])
        input_entity = await client.get_input_entity(channel_id)
    except Exception:
        input_entity = await client.get_input_entity(channel_info["url"])
    entity = types.InputPeerChannel(
        channel_id=input_entity.channel_id,
        access_hash=input_entity.access_hash
    )
    return entity


async def get_channel_or_megagroup(
        client, channel: Union[str, dict, int]):
    try:
        channel = int(channel)
    except Exception:
        pass
    try:
        channel = await get_input_entity(client, channel)
    except Exception:
        pass

    cha = await client(
        functions.channels.GetFullChannelRequest(
            channel=channel
        ))
    return cha.to_dict()


async def count_peer_messages(client, channel: dict):
    entity = await get_input_entity(client, channel)
    cha = await client(functions.messages.GetHistoryRequest(
        peer=entity, 
        limit=1,
        offset_id=0, 
        offset_date=None, 
        add_offset=0, 
        max_id=0, 
        min_id=0,
        hash=0
    ))
    msg_count = cha.to_dict()["count"]
    return {
        "chat": channel["id"],
        "msg_count": msg_count
    }


async def build_chat_info(tg_client, channel: str):
    """
    channel: must be the url of the channel, i.e. this method
        is generally called if a channel has been never seen
    """
    full_channel = await get_channel_or_megagroup(
        tg_client, channel
    )
    channel_id = int(full_channel["full_chat"]["id"])
    chat = full_channel["chats"][0]
    ts = dt.datetime.utcnow()
    ch_type = "group" if (
        chat["megagroup"] or chat["gigagroup"]) else "channel"
    record = {
        "id": channel_id,
        "url": channel,
        "username": chat["username"],
        "type": ch_type,
        "access_hash": chat["access_hash"],
        "about": full_channel["full_chat"]["about"],
        "title": chat["title"],
        "participants_count": full_channel["full_chat"][
            "participants_count"
        ],
        "inserted_at": ts,
        "updated_at": ts,
        
    }
    return record


async def update_chats_metadata(
    db: Session, client, channel_urls, sleep_per_request=3
):
    
    client_is_usable = await ut.client_is_logged_and_usable(client)
    if not client_is_usable:
        print(f"[update_chats_metadata: client is not usable")
        return 
    for url in channel_urls:
        print(f'Updating: {url}')
        channel = await uc.get_channel_by_url(db, url)  # it should return dict or None
        print(f'Channel in db: {channel}')
        if channel and not channel["id"]:  # this function works just on already initiated channels (url in db)
            print(f'{url} has not id and access_hash yet. Trying to retrieve entity info from Telegram')
            try:
                channel = await build_chat_info(client, url)
                print('Inserting entity info and metadata in db')
                await uc.upsert_channel_common(db, schemas.ChannelCommon(**channel))
            except Exception as e:
                print("Not able to get and save chat info because of error: " + str(e))
                print(f'Skipping {url}')
                await asyncio.sleep(sleep_per_request)
                continue  # try next channel in list
        if not channel:  # should never happen this
            continue  
        input_entity_info = {
            "id": int(channel["id"]),
            "access_hash": channel["access_hash"],
            "url": channel["url"]
        }
        count = await count_peer_messages(
            client, input_entity_info
        )
        info = await get_channel_or_megagroup(
            client, input_entity_info
        )
        pts_count = info["full_chat"]["participants_count"]
        # update channel in db. channel["url"] should be ok because they are initiated
        await uc.update_channel_common(db, channel["url"], {
            "messages_count": count["msg_count"],
            "participants_count": pts_count, 
            "updated_at": dt.datetime.utcnow()
        })
        await asyncio.sleep(sleep_per_request)

    