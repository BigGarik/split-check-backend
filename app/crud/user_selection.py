import json
import os

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.crud import get_users_by_check
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


async def get_user_selection_by_check_uuid(check_uuid: str):
    users = await get_users_by_check(check_uuid)
    logger.info(f"Получили пользователей: {', '.join([str(user) for user in users])}")
    participants = []
    for user in users:
        redis_key = f"user_selection:{user.id}:{check_uuid}"
        logger.info(f"Получили redis_key: {redis_key}")
        user_selection = await redis_client.get(redis_key)
        logger.info(f"Получили user_selection из redis: {user_selection}")
        if not user_selection:
            user_selection = await get_user_selection_by_user(user.id)
            logger.info(f"Получили user_selection из базы: {user_selection}")
            # Преобразуем строку JSON в словарь Python
        if user_selection:
            selection_data = json.loads(user_selection)
            logger.info(f"Получили selection_data: {selection_data}")

            # Создаем структуру для каждого участника
            participant = {
                "userid": user.id,
                "selectedItems": []
            }

            # Добавляем выбранные предметы пользователя
            for item in selection_data.get('selected_items', []):
                selected_item = {
                    "itemId": item['item_id'],
                    "quantity": item['quantity']
                }
                participant["selectedItems"].append(selected_item)

            participants.append(participant)
    return participants, users

