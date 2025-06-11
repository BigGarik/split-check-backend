import logging
import os
import uuid
from typing import Optional

from aiogram.utils.web_app import WebAppInitData, safe_parse_webapp_init_data
from dotenv import load_dotenv
from fastapi import Request, HTTPException
from starlette.status import HTTP_403_FORBIDDEN

from src.models import User
from src.repositories.user import get_user_by_email, create_new_user
from src.schemas import UserCreate

logger = logging.getLogger(__name__)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def tg_auth(request: Request, auto_error: bool = True) -> Optional[WebAppInitData]:
    try:
        auth_string = request.headers.get("initData", None)
        if auth_string:
            data = safe_parse_webapp_init_data(
                TELEGRAM_BOT_TOKEN,
                auth_string,
            )
            logger.debug(data)
            return data
        if auto_error:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
            )
        else:
            return None
    except Exception as e:
        if auto_error:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
            )
        else:
            return None


# Создаем отдельную функцию-обертку для использования в Depends
async def tg_auth_optional(request: Request) -> Optional[WebAppInitData]:
    """Обертка для tg_auth с auto_error=False для использования в Depends."""
    return await tg_auth(request, auto_error=False)


async def check_tg_user(tg_auth_data: WebAppInitData) -> User:
    tg_id = tg_auth_data.user.id
    nickname = tg_auth_data.user.username
    avatar_url = tg_auth_data.user.photo_url
    email = f'{tg_id}@t.me'
    user = await get_user_by_email(email)
    if not user:
        user = await create_new_user(
            user_data=UserCreate(
                email=email,
                password=uuid.uuid4().hex
            ),
            profile_data={
                "nickname": nickname,
                "avatar_url": avatar_url
            }
        )

    return user
