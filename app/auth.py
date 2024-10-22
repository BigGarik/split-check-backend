import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.crud import get_user_by_email

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
algorithm = os.getenv('ALGORITHM')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user or not await verify_password(password, user.hashed_password):
        return False
    return user


# Функция для создания токена
async def create_token(data: dict, token_expire_minutes: int, secret_key: str):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


# Проверка токена
async def verify_token(secret_key: str, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except JWTError:
        raise credentials_exception


# Получаем текущего пользователя из токена
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        email = await verify_token(access_secret_key, token=token)
        user = await get_user_by_email(email)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
