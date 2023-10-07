from fastapi import APIRouter, Depends, HTTPException
import fastapi
from tinydb import Query
from teledash import models
from teledash import config
from teledash.utils.db import user as uu
from typing import List
from sqlalchemy.orm import Session
from email_validator import validate_email
from teledash.utils.admin import set_disabled
from teledash.db.db_setup import get_db
import os
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
    only_active: bool = False,
    db: Session = Depends(get_db)
):  
    try:
        response = uu.get_all_usernames(db)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

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


@admin_router.get(
    '/db_sql_file',
    response_class=fastapi.responses.FileResponse
)
async def download_sql_file_of_app_db(
    path_rel_to_session_folder="teledash.db"
):
    
    file_path = os.path.join(config.SESSIONS_FOLDER, path_rel_to_session_folder)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail=f"File {file_path} does not exist")
    return fastapi.responses.FileResponse(file_path)
    