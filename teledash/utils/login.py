from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Union
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from teledash import schemas
from teledash.config import settings
from teledash import config
from tinydb import Query
from email_validator import validate_email
from teledash.config import settings
from fastapi.responses import RedirectResponse
from teledash.utils.db import user as uu
from sqlalchemy.orm import Session
from teledash.db.db_setup import get_db
try:
    from typing import Annotated
except Exception:
    from typing_extensions import Annotated

manager = settings.MANAGER
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
reuseable_oauth = OAuth2PasswordBearer(
    # tokenUrl=f"{settings.API_V1_STR}/auth/login",
    tokenUrl='login',
    scheme_name="JWT"
)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


""" def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return models.UserInDB(**user_dict) """


@manager.user_loader()
def get_user(
    username_or_email: str
):
    db = next(get_db())
    try:
        validate_email(username_or_email)
        user = uu.get_user_by_email(db, username_or_email)
    except Exception:
        user = uu.get_user_by_username(db, username_or_email)
    if user and not user.to_dict().get("disabled", False):
        return schemas.UserInDB(**user.to_dict())
    

def authenticate_user(
        db: Session, username_or_email: str, password: str):
    user = get_user(username_or_email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(
    data: dict, 
    expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, 
        algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict, 
    expires_delta: Union[timedelta, None] = None) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, 
        settings.ALGORITHM
        )
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(reuseable_oauth)],
) -> schemas.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        token_data = schemas.TokenPayload(**payload)
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.sub)
    if not user:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)]
):
    
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def auth_exception_handler(request, exc):
    """
    https://stackoverflow.com/questions/73630653

    Redirect the user to the login page if not logged in
    """
    
    return RedirectResponse(
        url='/app_login?next=' + str(request.url)
    )