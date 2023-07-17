from teledash import config
import os
from teledash import models



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
