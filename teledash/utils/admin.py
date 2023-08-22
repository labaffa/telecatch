from tinydb import Query
from email_validator import validate_email
from teledash import config
import fastapi


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
