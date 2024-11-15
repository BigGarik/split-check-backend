import json

from fastapi import Depends
from loguru import logger

from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.managers.check_manager import CheckManager, get_check_manager
from src.repositories.profile import get_user_profile_db, update_user_profile_db
from src.schemas import UserProfileUpdate, UserProfileBase, UserProfileResponse


async def get_user_profile_task(user_id: int):
    """Получить профиль текущего пользователя"""
    logger.debug(f"user_id: {user_id}")
    profile = await get_user_profile_db(user_id)
    if profile:
        # Преобразуем SQLAlchemy модель в Pydantic модель
        profile_response = UserProfileResponse.model_validate(profile)

        profile_payload = UserProfileBase(
            nickname=profile_response.nickname,
            language=profile_response.language,
            avatar_url=profile_response.avatar_url
        ).model_dump()

        # Создаем структуру сообщения
        msg = {
            "type": settings.Events.USER_PROFILE_DATA_RECEIVED_EVENT,
            "payload": profile_payload
        }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )


async def update_user_profile_task(user_id: int,
                                   profile_data: UserProfileUpdate,
                                   check_manager: CheckManager = Depends(get_check_manager)):
    """Обновить профиль текущего пользователя"""
    logger.debug(f"profile_data: {profile_data}")
    profile = await update_user_profile_db(user_id, profile_data)
    if profile:
        # Преобразуем SQLAlchemy модель в Pydantic модель
        profile_response = UserProfileResponse.model_validate(profile)

        # Создаем payload только с нужными полями
        profile_payload = {
            "nickname": profile_response.nickname,
            "language": profile_response.language,
            "avatar_url": profile_response.avatar_url
        }

        # Создаем структуру сообщения
        msg = {
            "type": settings.Events.USER_PROFILE_DATA_UPDATE_EVENT,
            "payload": profile_payload
            }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )
