from tinydb import Query
from email_validator import validate_email
from teledash import config
import fastapi
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import fastapi
from teledash.config import settings
import jwt


def derive_key_from_password(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  
        salt=salt,
        iterations=100000,  
        backend=default_backend()
    )
    return kdf.derive(password.encode()) 


def encrypt_data(key, data):
    nonce = os.urandom(12)  
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data.encode(), None)
    return nonce + ciphertext  


def decrypt_data(key, encrypted_data):
    nonce = encrypted_data[:12]  
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


def enc_key_from_cookies(request: fastapi.Request):
    key_cookie = jwt.decode(
            request.cookies.get("key_hash"),
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
        ).get("sub")
    if not key_cookie:
        return None
    enc_key_encrypted = bytes.fromhex(key_cookie)
    enc_key = bytes.fromhex(decrypt_data(settings.DATA_SECRET_KEY.encode(), enc_key_encrypted))
    return enc_key


async def set_disabled(
    username_or_email: str, disable: bool
):
    User = Query()
    try:
        validate_email(username_or_email)
        field = "email"
    except Exception:
         field = "username"
    
    user_in_db = config.db.table("users").search(
        User[field] == username_or_email
    )
    if not user_in_db:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="There is no account with this username"
        )
    disabled = True if disable else False
    config.db.table("users").update(
        {"disabled": disabled},
        User[field] == username_or_email
    )
    updated_user = config.db.table("users").search(
        User[field] == username_or_email
    )[0]
    return updated_user
