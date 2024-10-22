import json
import os

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import get_async_db
from app.models import UserSelection
from app.redis import redis_client
from app.schemas import CheckSelectionRequest

load_dotenv()

redis_expiration = os.getenv("REDIS_EXPIRATION")


async def add_or_update_user_selection(user_id: int, check_uuid: str, selection_data: CheckSelectionRequest):
    """
    Добавить или обновить запись в таблице user_selections.
    Если запись существует, она будет обновлена, если нет — будет создана новая запись.

    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные, которые нужно сохранить в формате JSON
    """
    redis_key = f"user_selection:{user_id}:{check_uuid}"
    await redis_client.set(redis_key, json.dumps(selection_data.dict()), expire=redis_expiration)
    async with get_async_db() as session:
        try:
            # Проверяем, существует ли запись с таким user_id и check_uuid
            stmt = select(UserSelection).filter_by(user_id=user_id, check_uuid=check_uuid)
            result = await session.execute(stmt)
            user_selection = result.scalars().first()

            if user_selection:
                user_selection.selection = selection_data.dict()
                logger.info(f"Запись для user_id={user_id}, check_uuid={check_uuid} обновлена.")
            else:
                # Запись не найдена, создаём новую
                new_selection = UserSelection(
                    user_id=user_id,
                    check_uuid=check_uuid,
                    selection=selection_data.dict()
                )
                session.add(new_selection)
                logger.info(f"Создана новая запись для user_id={user_id}, check_uuid={check_uuid}.")

            # Сохраняем изменения в базе данных
            await session.commit()

        except IntegrityError as e:
            await session.rollback()  # Откат транзакции в случае ошибки
            logger.error(f"Ошибка добавления или обновления записи: {e}")
            raise


async def get_user_selection_by_user(user_id: int):
    async with get_async_db() as session:
        stmt = select(UserSelection).filter_by(user_id=user_id)
        result = await session.execute(stmt)
        user_selections = result.scalars().first()
        return user_selections
