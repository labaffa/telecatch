import fastapi
from teledash.utils.login import create_access_token, \
    get_password_hash, authenticate_user, \
    create_refresh_token, get_current_active_user
from teledash import models
from uuid import uuid4
from teledash import config
from tinydb import Query
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from teledash.utils.telegram import create_client


user_db = config.db.table("users")
User = Query()
api_login_router = fastapi.APIRouter()
templates = Jinja2Templates(directory="teledash/templates")


@api_login_router.post(
    '/signup', 
    summary="Create new user", 
    response_model=models.User)
async def create_user(data: models.UserAuth):
    # querying database to check if user already exist
    detail = None
    user_by_email = user_db.search(User.email == data.email)
    user_by_name = user_db.search(User.username == data.username)
    if user_by_email and user_by_name:
        detail = "Email and username already exist"
    elif user_by_name and not user_by_email:
        detail = "User with this username already exists"
    elif user_by_email and not user_by_name:
        detail = "User with this email already exists"
    if user_by_name or user_by_email:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
    user = {
        'email': data.email,
        'username': data.username,
        'user_id': str(uuid4())
    }
    user_in_db = dict(user)
    user_in_db["hashed_password"] = get_password_hash(data.password)
    user_db.insert(dict(models.UserInDB(**user_in_db)))   # saving user to database
    return user


@api_login_router.post(
    '/login', 
    summary="Create access and refresh tokens for user", 
    response_model=models.Token   
)
async def login_to_app_account(
    response: fastapi.Response,
    form_data: Annotated[
        OAuth2PasswordRequestForm, fastapi.Depends()]):
    user = authenticate_user(
        # config.db.table("users"), 
        form_data.username, form_data.password
    )
    if not user:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.username}
    )
    credentials = {
        "access_token": access_token,
        "refresh_token": create_refresh_token(
            data={"sub": user.username}),
        "token_type": "bearer"
    }
    config.settings.MANAGER.set_cookie(response, access_token)
    return credentials


@api_login_router.get(
    '/logout', response_class=HTMLResponse)
def logout_from_app(
    request: fastapi.Request, 
    user=fastapi.Depends(config.settings.MANAGER)):
    resp = RedirectResponse(
        url=dict(request.query_params).get("next", "/"),  # redirect to same page but logged out
        status_code=fastapi.status.HTTP_302_FOUND
    )
    config.settings.MANAGER.set_cookie(resp, "")
    return resp


@api_login_router.get("/users/me/", response_model=models.User)
async def read_users_me(
    current_user: Annotated[
        models.User, 
        fastapi.Depends(get_current_active_user)
        ]
    ):
    return current_user


@api_login_router.post("/add_tg_phone")
async def add_phone_to_user(
    request: fastapi.Request,
    phone: Annotated[str, fastapi.Form()],
    api_id: Annotated[int, fastapi.Form()],
    api_hash: Annotated[str, fastapi.Form()],
    code: Annotated[int, fastapi.Form()] = None,
    user=fastapi.Depends(config.settings.MANAGER)
):
    TgClient = Query()
    UserTg = Query()
    client_in_db = config.db.table("tg_clients").search(
        (TgClient.phone == phone) &
        (TgClient.api_id == api_id) &
        (TgClient.api_hash == api_hash)
    )
    client_in_db = client_in_db[0] if client_in_db else {}
    authenticated = client_in_db.get("authenticated", False)
    client_dict = await create_client(
        phone, api_id, api_hash, code, authenticated,
    )
    tg_client = {
        "client_id": client_dict["session_file"],
        "phone": phone,
        "api_id": api_id,
        "api_hash": api_hash
    }
    config.db.table("users_clients").upsert(
            {
                "user_id": user.user_id, 
                "client_id": tg_client["client_id"]
            },
            (UserTg.user_id == user.user_id) &
            (UserTg.client_id == tg_client["client_id"])
    )
    if client_dict["status"] != "ok":
        tg_client["authenticated"] = False
        config.db.table("tg_clients").upsert(
            tg_client,
            (TgClient.client_id == tg_client["client_id"]) 
        )
        
        return client_dict
    
    tg_client["authenticated"] = True
    config.db.table("tg_clients").upsert(
        tg_client,
        TgClient.client_id == tg_client["client_id"]
    )
    account = config.db.table("tg_clients").search(
       TgClient.client_id == tg_client["client_id"]
    )
    return account






