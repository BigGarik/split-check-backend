import json
import os

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.crud import get_users_by_check_uuid
from app.database import get_async_db
from app.models import UserSelection
from app.redis import redis_client
from app.schemas import CheckSelectionRequest

load_dotenv()

redis_expiration = os.getenv("REDIS_EXPIRATION")


async def add_or_update_user_selection(user_id: int, check_uuid: str, selection_data):
    """
    Добавить или обновить запись в таблице user_selections.
    Если запись существует, она будет обновлена, если нет — будет создана новая запись.
    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные, которые нужно сохранить в формате JSON
    """
    try:
        async with get_async_db() as session:
            # Проверяем, существует ли запись с таким user_id и check_uuid
            stmt = select(UserSelection).filter_by(user_id=user_id, check_uuid=check_uuid)
            result = await session.execute(stmt)
            user_selection = result.scalars().first()

            # Обновляем или создаем новую запись
            if user_selection:
                user_selection.selection = selection_data
                logger.info(f"Запись для user_id={user_id}, check_uuid={check_uuid} обновлена.")
            else:
                new_selection = UserSelection(
                    user_id=user_id,
                    check_uuid=check_uuid,
                    selection=selection_data
                )
                session.add(new_selection)
                logger.info(f"Создана новая запись для user_id={user_id}, check_uuid={check_uuid}.")

            # Сохраняем изменения в базе данных
            await session.commit()

            # После успешного сохранения в БД — добавляем данные в Redis
            redis_key = f"user_selection:{user_id}:{check_uuid}"
            await redis_client.set(redis_key, json.dumps(selection_data), expire=redis_expiration)
            logger.info(f"Данные сохранены в Redis для ключа {redis_key}")

    except Exception as e:
        # Откат транзакции в случае ошибки
        await session.rollback()
        logger.error(f"Ошибка добавления или обновления записи: {e}")

        # Поднимаем общее исключение с деталями ошибки
        raise Exception(f"Ошибка при обновлении данных пользователя: {str(e)}")


async def get_user_selection_by_user(user_id: int, check_uuid: str):
    async with get_async_db() as session:
        stmt = select(UserSelection).filter_by(user_id=user_id, check_uuid=check_uuid)
        result = await session.execute(stmt)
        user_selections = result.scalars().first()
        return user_selections


async def get_user_selection_by_check_uuid(check_uuid: str):
    users = await get_users_by_check_uuid(check_uuid)
    logger.info(f"Получили пользователей: {', '.join([str(user) for user in users])}")

    participants = []

    for user in users:
        redis_key = f"user_selection:{user.id}:{check_uuid}"
        logger.info(f"Получили redis_key: {redis_key}")

        # Пытаемся получить данные из Redis
        user_selection = await redis_client.get(redis_key)
        logger.info(f"Получили user_selection из redis: {user_selection}")

        # Если данных нет в Redis, берем из базы данных
        if not user_selection:
            user_selection = await get_user_selection_by_user(user.id, check_uuid)

        # Если user_selection — это объект, нам нужно извлечь поле selection
        if user_selection:
            if isinstance(user_selection, str):
                # Если данные пришли из Redis в виде строки, преобразуем их
                selection_data = json.loads(user_selection)
            else:
                # Если данные пришли из базы, то это объект SQLAlchemy
                selection_data = user_selection.selection  # Это поле должно быть JSON (dict)
                logger.info(f"Получили user_selection из базы: {user_selection}")

            logger.info(f"Получили selection_data: {selection_data}")

            # Создаем структуру для каждого участника
            participant = {
                "user_id": user.id,
                "selected_items": []
            }

            # Добавляем выбранные позиции пользователя
            for item in selection_data.get('selected_items', []):
                selected_item = {
                    "item_id": item['item_id'],
                    "quantity": item['quantity']
                }
                participant["selected_items"].append(selected_item)

            participants.append(participant)

    logger.info(f"Получили participants: {participants}")

    return json.dumps(participants), users


