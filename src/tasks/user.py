import json
import logging

from src.config import config
from src.config.type_events import Events
from src.repositories.profile import get_user_profile_db, update_user_profile_db, get_user_email
from src.repositories.user import user_delete
from src.schemas import UserProfileBase, UserProfileResponse
from src.websockets.manager import ws_manager

logger = logging.getLogger(config.app.service_name)


async def get_user_profile_task(user_id: int):
    """Получить профиль текущего пользователя"""
    profile = await get_user_profile_db(user_id)

    email = await get_user_email(user_id)

    logger.debug(f"email: {email}")

    if profile:
        # Преобразуем SQLAlchemy модель в Pydantic модель
        profile_response = UserProfileResponse.model_validate(profile)

        profile_payload = UserProfileBase(
            nickname=profile_response.nickname,
            language=profile_response.language,
            avatar_url=profile_response.avatar_url
        ).model_dump()
        profile_payload["email"] = email

        # Создаем структуру сообщения
        msg = {
            "type": Events.USER_PROFILE_DATA_RECEIVED_EVENT,
            "payload": profile_payload
        }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )


async def update_user_profile_task(user_id: int,
                                   profile_data: str):
    """Обновить профиль текущего пользователя"""
    profile_data = json.loads(profile_data)
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
            "type": Events.USER_PROFILE_DATA_UPDATE_EVENT,
            "payload": profile_payload
            }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )


async def user_delete_task() -> None:
    await user_delete()