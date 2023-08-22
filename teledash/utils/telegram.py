"""
Largely taken from 

https://github.com/digitalmethodsinitiative/4cat/blob/master/datasources/telegram/search_telegram.py
"""
from pathlib import Path
import hashlib
from telethon import TelegramClient
from teledash import config
import asyncio
from tinydb import Query
import fastapi


class NeedsCodeException(Exception):
    pass


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


def cancel_start():
    """
    Replace interactive phone number input in Telethon

    By default, if Telethon cannot use the given session file to
    authenticate, it will interactively prompt the user for a phone
    number on the command line. That is not useful here, so instead
    raise a RuntimeError. This will be caught below and the user will
    be told they need to re-authenticate via 4CAT.
    """
    raise RuntimeError("Connection cancelled")


async def create_client(
    phone, api_id, api_hash, code=None, 
    authenticated=False
):
    session_id = create_session_id(
        phone, api_id, api_hash
    )
    session_file = session_id + '.session'
    session_path = Path(config.SESSIONS_FOLDER).joinpath(
        session_file
    )
    
    client = None
    out = None

    if authenticated:  # not first login
        try:
            client = TelegramClient(
                str(session_path), int(api_id), api_hash
            )
            await client.start(phone=phone)
            out = {
                "needs_code": False,
                "client": client,
                "detail": "login done",
                "status": "ok",
                "session_file": session_file
            }
        except Exception as e:
            # session is no longer useable, delete file so user will be asked
            # for security code again. The RuntimeError is raised by
            # `cancel_start()`
            
            out = {
                "needs_code": True,
                "client": None,
                "detail": str(e),
                "status": "failed",
                "session_file": session_file
            }
        finally:
            if client and hasattr(client, "disconnect"):
                await client.disconnect()
    else:
        
        try:
            await first_login(
                phone, api_id, api_hash, code=code
            )
            out = {
                "needs_code": False,
                "client": client,
                "detail": "login done",
                "status": "ok",
                "session_file": session_file
            }
        except NeedsCodeException:
            out = {
                "needs_code": True,
                "client": None,
                "status": "pending",
                "detail": "security code sent",
                "session_file": session_file
            }
    return out
        

async def first_login(phone, api_id, api_hash, code=None):
    session_id = create_session_id(
        phone, api_id, api_hash
    )
    session_path = Path(config.SESSIONS_FOLDER).joinpath(
        session_id + '.session')
    if code is not None:
        code_callback = lambda: int(code)
        max_attempts = 1
    else:
        # if code is None, it means we havent'passed a code
        # and we need to send a code request. here we make 
        # the function raise exception to exit and, if 
        # we received the code from telegram we should 
        # call this function again passing that code
        code_callback = lambda: -1
        max_attempts = 0

    needs_code = False
    try:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = TelegramClient(str(session_path), api_id, api_hash, loop=loop)
            await client.start(
                max_attempts=max_attempts, 
                phone=phone, 
                code_callback=code_callback
            )
        except RuntimeError as e:
            # A code was sent to the given phone number
            needs_code = True
    except Exception:
        raise  # maybe change this behavior
    finally:
        if client and hasattr(client, "disconnect"):
            await client.disconnect()
    if needs_code:
        raise NeedsCodeException
    return client


async def get_authenticated_client(client_id: str):
    session_path = Path(config.SESSIONS_FOLDER).joinpath(
        client_id
    )
    try:
        client_in_db = config.db.table("tg_clients").search(
            Query().client_id == client_id
        )[0]
    except IndexError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="client not present in db (not registered)"
        )
    if not client_in_db["authenticated"]:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="client not authenticated"
        )
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = TelegramClient(
            str(session_path), 
            client_in_db["api_id"], 
            client_in_db["api_hash"], 
            loop=loop)
        await client.start()
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    return client

