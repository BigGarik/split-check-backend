import json
import os
from loguru import logger
from dotenv import load_dotenv

from app.crud import get_user_profile_db, update_user_profile_db
from app.routers.ws import ws_manager
from app.schemas import UserProfileUpdate, UserProfileBase, UserProfileResponse

load_dotenv()


async def get_user_profile(user_id: int):
    """Получить профиль текущего пользователя"""
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
            "type": "userProfileDataReceivedEvent",
            "payload": profile_payload
        }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )


async def update_user_profile(user_id: int, profile_data: UserProfileUpdate):
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
            "type": "userProfileDataUpdateEvent",
            "payload": profile_payload
            }

        logger.debug(f"msg: {msg}")

        await ws_manager.send_personal_message(
            message=json.dumps(msg, default=str),  # Добавляем default=str для обработки дат
            user_id=user_id
        )


if __name__ == '__main__':
    pass
