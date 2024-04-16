"""
Largely taken from 

https://github.com/digitalmethodsinitiative/4cat/blob/master/datasources/telegram/search_telegram.py
"""
from pathlib import Path
import hashlib
from telethon import TelegramClient, types
from teledash import config, schemas
import asyncio
import fastapi
from teledash.utils.db import tg_client as ut
from teledash.utils.db import channel as uc
from sqlalchemy.orm import Session
import re


class NeedsCodeException(Exception):
    pass


def parse_phone(phone):
    """Parses the given phone, or returns `None` if it's invalid."""
    if isinstance(phone, int):
        return str(phone)
    else:
        phone = re.sub(r'[+()\s-]', '', str(phone))
        if phone.isdigit():
            return phone


def create_session_id(phone_or_bot_token, api_id, api_hash, phone=True):
    """
    Generate a filename for the session file

    This is a combination of phone number and API credentials, but hashed
    so that one cannot actually derive someone's phone number from it.

    :param str api_phone:  Phone number for API ID
    :param int api_id:  Telegram API ID
    :param str api_hash:  Telegram API Hash
    :return str: A hash value derived from the input
    """
    if phone:
        phone_or_bot_token = phone_or_bot_token.strip().replace("+", "")
    
    hash_base = phone_or_bot_token + str(api_id).strip() + api_hash.strip()
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


async def create_bot_client(
    bot_token, api_id, api_hash, *args
):
    session_id = create_session_id(
        bot_token, api_id, api_hash, phone=False
    )
    session_file = session_id + '.session'
    session_path = Path(config.SESSIONS_FOLDER).joinpath(
        session_file
    )
    
    client = None
    
    try:

        client = TelegramClient(
            str(session_path), int(api_id), api_hash
        )
        await client.start(bot_token=bot_token)
        out = {
            "needs_code": False,
            "client": client,
            "detail": "login done",
            "status": "ok",
            "session_file": session_file
        }
    except Exception as e:
        print(f"problem authenticating bot due to {str(e)}")
        out = {
            "needs_code": False,
            "client": None,
            "detail": str(e),
            "status": "failed",
            "session_file": session_file
        }
    finally:
        if client and hasattr(client, "disconnect"):
            await client.disconnect()
    return out


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
            print("[create client]: error on using authenticated client")
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
            print("[create client]: first login")
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
    if code:
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
    except Exception as e:
        print("Error: ", str(e))
        print("[first login]: deleting and creating new session file")

        if session_path.exists():
            session_path.unlink()
        
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
    finally:
        if client and hasattr(client, "disconnect"):
            await client.disconnect()
    if needs_code:
        raise NeedsCodeException
    return client


async def is_client_authenticated(client_instance):
    await client_instance.connect()
    if await client_instance.is_user_authorized():
        response = True
    else:
        response = False
    if client_instance and hasattr(client_instance, "disconnect"):
        client_instance.disconnect()
    return response


async def started_client(session_path, api_id, api_hash):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        client = TelegramClient(
            session_path, 
            api_id, 
            api_hash, 
            loop=loop
        )
        await client.start()
        return client
    except Exception as e:
        loop.stop()
        loop.close()
        print(str(e))


async def client_is_logged_and_usable(client_instance):
    response = False
    try:
        await client_instance.connect()
        if (await client_instance.is_user_authorized()):
            response = True
    except Exception as e:
        print("[client_is_logged_and_usable]: ", str(e))
    return response


async def get_authenticated_client(
    db: Session, client_id: str
):
    
    """ TODO: should we use httpexception here???"""
    session_path = Path(config.SESSIONS_FOLDER).joinpath(
        client_id
    )
    print("[get_authenticated]: ", client_id)
    client_in_db = await ut.get_client_meta(db, client_id)
    if not client_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="client not present in db (not registered)"
        )
    client_in_db = client_in_db.to_dict()
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
            loop=loop
        )
        is_usable = await client_is_logged_and_usable(client)
        print("[get_authenticated]: ", is_usable)
        if not is_usable:
            return None
        await client.start()

        # client = await started_client(
        #     str(session_path), client_in_db["api_id"], client_in_db["api_hash"]
        # )

        """ client_authenticated = await is_client_authenticated(client)
        if not client_authenticated:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
                detail="client not authenticated"
            ) """
    except Exception as e:
        # loop.close()
        # it never enters here because a try except is inside started_client
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    return client

    
# async def client_is_logged_and_usable(client_id: str, api_id: int, api_hash: str):
#     client_works = False
#     session_path = Path(config.SESSIONS_FOLDER).joinpath(
#         client_id
#     )
#     try:
#         client = TelegramClient(
#             session_path.as_posix(), int(api_id), api_hash
#         )
#         await client.connect()
#         if await client.is_user_authorized():
#             client_works = True
#         client.disconnect()
#     except Exception as e:
#         print(str(e))
#     return client_works


