from fastapi import APIRouter
from tinydb import Query
from teledash import models
from teledash import config
from typing import List
from email_validator import validate_email
from teledash.utils.admin import set_disabled
try:
    from typing import Annotated
except Exception:
    from typing_extensions import Annotated


admin_router = APIRouter()


@admin_router.get(
    '/all_users',
    summary="Get list of all users in db",
    response_model=List[dict]
)
async def get_a_list_of_registered_users(
    only_active: bool = False
):  
    User = Query()
    if only_active:
        result = config.db.table("users").search(
            User.disabled == False
        )
    else:
        result = config.db.table("users").all()
    return result


@admin_router.put(
    '/disable_account',
    summary="Disable an active account",
    response_model=models.User
)
async def disable_account(
    username_or_email: Annotated[str, "Exact username"]
):  
    updated_user = await set_disabled(
        username_or_email, disable=True
    )
    return updated_user


@admin_router.put(
    '/enable_account',
    summary="Enable a disactive account",
    response_model=models.User
)
async def disable_account(
    username_or_email: Annotated[str, "Exact username"]
):  
    updated_user = await set_disabled(
        username_or_email, disable=False
    )
    return updated_user


    
    