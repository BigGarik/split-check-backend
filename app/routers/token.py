import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError

from app.auth import authenticate_user, create_token, verify_token
from app.schemas import RefreshTokenRequest

load_dotenv()

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_MINUTES'))


router = APIRouter(prefix="/token", tags=["token"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Эндпоинт для получения access_token и refresh_token
@router.post("")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Аутентификация пользователя
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Создаем Access и Refresh токены
    access_token = await create_token(
        data={"email": user.email, "user_id": user.id},
        token_expire_minutes=access_token_expire_minutes,
        secret_key=access_secret_key
    )
    refresh_token = await create_token(
        data={"email": user.email, "user_id": user.id},
        token_expire_minutes=refresh_token_expire_days,
        secret_key=refresh_secret_key
    )

    # 3. Возвращаем токены
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh")
async def refresh_access_token(request: RefreshTokenRequest):
    refresh_token = request.refresh_token
    try:
        # 1. Проверка Refresh токена
        email, user_id = await verify_token(secret_key=refresh_secret_key, token=refresh_token)

        # 2. Создаем новый Access токен
        new_access_token = await create_token(
            data={"email": email, "user_id": user_id},
            token_expire_minutes=access_token_expire_minutes,
            secret_key=access_secret_key
        )
        # 3. Создаем новый Refresh токен
        new_refresh_token = await create_token(
            data={"email": email, "user_id": user_id},
            token_expire_minutes=refresh_token_expire_days,
            secret_key=refresh_secret_key
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
