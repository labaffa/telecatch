from teledash import config
import os
from teledash import models
import hashlib


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



async def count_peer_messages(client, peer, limit=100, offset_id=0):
    """ count = 0
    async with client:
        async for _ in client.iter_messages(peer):
            count += 1
    return {"count": count} """
    async with client:
        ch = await client.get_input_entity(peer)
        cha = await client(functions.messages.GetHistoryRequest(
            peer=ch, limit=1,
            offset_id=0, offset_date=None, add_offset=0, max_id=0, min_id=0,
            hash=0
    ))
    return cha.stringify()
