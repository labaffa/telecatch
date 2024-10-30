import fastapi
from teledash.db.models import User
from teledash.utils.users import active_user
from teledash import schemas
from fastapi.templating import Jinja2Templates
from teledash.utils.telegram import create_client, \
    create_session_id, get_authenticated_client, client_is_logged_and_usable
import pandas as pd
import io
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_async_session
from teledash.utils.db import tg_client as ut
import numpy as np
try:
    from typing import Annotated
except Exception:
    from typing_extensions import Annotated


api_login_router = fastapi.APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


# @api_login_router.post(
#     '/signup', 
#     summary="Create new user", 
#     response_model=models.UserInDB
# )
# async def create_user(
#     data: models.UserAuth,
#     db: Session = fastapi.Depends(get_db)
# ):
#     # querying database to check if user already exist
#     detail = None
#     # user_by_email = user_db.search(User.email == data.email)
#     # user_by_name = user_db.search(User.username == data.username)
    
#     user_by_email = uu.get_user_by_email(db=db, email=data.email)
#     user_by_name = uu.get_user_by_username(
#         db=db, username=data.username
#     )
#     if user_by_email and user_by_name:
#         detail = "Email and username already exist"
#     elif user_by_name and not user_by_email:
#         detail = "User with this username already exists"
#     elif user_by_email and not user_by_name:
#         detail = "User with this email already exists"
#     if user_by_name or user_by_email:
#         raise fastapi.HTTPException(
#             status_code=fastapi.status.HTTP_400_BAD_REQUEST,
#             detail=detail
#         )
#     user = {
#         'email': data.email,
#         'username': data.username,
#         # 'user_id': str(uuid4())
#     }
#     user_in_db = dict(user)
#     user_in_db["hashed_password"] = get_password_hash(data.password)

#     # user_db.insert(dict(models.UserInDB(**user_in_db)))   # saving user to database
#     return uu.create_user(db=db, user=user_in_db).to_dict()


# @api_login_router.post(
#     '/login', 
#     summary="Create access and refresh tokens for user", 
#     response_model=models.Token   
# )
# async def login_to_app_account(
#     response: fastapi.Response,
#     form_data: Annotated[
#         OAuth2PasswordRequestForm, fastapi.Depends()],
#     db: Session = fastapi.Depends(get_db)
# ):
#     user = authenticate_user(
#         # config.db.table("users"), 
#         db, form_data.username, form_data.password
#     )
#     if not user:
#         raise fastapi.HTTPException(
#             status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token = create_access_token(
#         data={"sub": user.username}
#     )
#     credentials = {
#         "access_token": access_token,
#         "refresh_token": create_refresh_token(
#             data={"sub": user.username}),
#         "token_type": "bearer"
#     }
#     config.settings.MANAGER.set_cookie(response, access_token)
#     return credentials


# @api_login_router.get(
#     '/logout', response_class=HTMLResponse)
# def logout_from_app(
#     request: fastapi.Request, 
#     user=fastapi.Depends(config.settings.MANAGER)):
#     resp = RedirectResponse(
#         url=dict(request.query_params).get("next", "/"),  # redirect to same page but logged out
#         status_code=fastapi.status.HTTP_302_FOUND
#     )
#     config.settings.MANAGER.set_cookie(resp, "")
#     return resp


# @api_login_router.get("/users/me/", response_model=models.User)
# async def read_users_me(
#     current_user: Annotated[
#         models.User, 
#         fastapi.Depends(get_current_active_user)
#         ]
#     ):
#     return current_user


@api_login_router.post("/add_tg_phone")
async def add_phone_to_user(
    request: fastapi.Request,
    phone: Annotated[str, fastapi.Form()],
    api_id: Annotated[int, fastapi.Form()],
    api_hash: Annotated[str, fastapi.Form()],
    code: Annotated[int, fastapi.Form()] = None,
    user: User = fastapi.Depends(active_user),
    db: Session = fastapi.Depends(get_async_session)
):
    try:
        session_id = create_session_id(phone, api_id, api_hash)
        client_id = session_id + '.session'
        
        
        client_in_db = await ut.get_client_meta(db, client_id)
        client_in_db = client_in_db.to_dict() if client_in_db else {}
        authenticated = client_in_db.get("authenticated", False)
        
        # authenticated = await client_is_logged_and_usable(client_id, api_id, api_hash)
        print("authenticated: ", authenticated)
        try:
            client_used_by_app = request.app.state.clients.get(client_id)
        except Exception:
            client_used_by_app = None
        if client_used_by_app:
            print("[add_tg_phone]: client in app")
            await ut.upsert_user_client_relation(
                db=db, user_id=user.id, client_id=client_id
            )
            is_usable = await client_is_logged_and_usable(client_used_by_app)
            print("[add_tg_phone] is usable: ", is_usable)
            if is_usable:
                return client_in_db
            else:
                authenticated = False
        else:
            authenticated = False
        print("[add_tg_phone]: creating client")   
        client_dict = await create_client(
            phone, api_id, api_hash, code, authenticated,
        )
        tg_client = {
            "id": client_dict["session_file"],
            "phone": phone,
            "api_id": api_id,
            "api_hash": api_hash
        }
        tg_client["authenticated"] = True if (client_dict["status"] == "ok") else False    
        await ut.upsert_tg_client(db=db, row_dict=tg_client)
        await ut.upsert_user_client_relation(
            db=db, user_id=user.id, client_id=client_id
        )
        if tg_client["authenticated"]:
            request.app.state.clients[client_id] = await get_authenticated_client(
                db, client_id
            )
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=[{"msg": str(e)}]
        )
    return tg_client


@api_login_router.post("/uploadfile")
async def upload_entities(file: fastapi.UploadFile):
    
    content = await file.read()
    error = None
    data = []
    try:
        # Try parsing as CSV
        df = pd.read_csv(
            io.BytesIO(content), 
            sep=None, 
            engine="python",
            encoding="ISO-8859-1"
            
        )
    
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise fastapi.HTTPException(
                status_code=400, 
                detail="File could not be parsed. Try to use .xls, .xlsx, .csv, .tsv"
            )
    try:
        df.columns = df.columns.str.lower()
        df = df.replace({np.nan: None})
        for row in df.to_dict("records"):
            row = schemas.ChannelUpload(**row).model_dump()
            data.append(row)
        return {
            "message": "File ok",
            "error": error,
            "rows": data
        }
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=400, detail=str(e)
        )
    

@api_login_router.get("/check_client")
async def check_if_a_client_is_logged_in(
    request: fastapi.Request, client_id: str, api_id: int, api_hash: str
):
    response = False
    client_instance_in_app = request.app.state.clients.get(client_id)
    if client_instance_in_app:
        response = await client_is_logged_and_usable(client_instance_in_app)
    return response






