import json
import logging

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import REDIS_EXPIRATION
from src.models import UserSelection, SelectedItem
from src.redis import redis_client
from src.repositories.user import get_users_by_check_uuid

logger = logging.getLogger(__name__)


async def add_or_update_user_selection(session: AsyncSession, user_id: int, check_uuid: str, selection_data: dict):
    """
    Добавить или обновить запись в таблице user_selections и связанные записи в selected_items.
    Если запись UserSelection существует, обновляет связанные SelectedItem, если нет — создаёт новую.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные о выбранных элементах в формате {"selected_items": [{"item_id": int, "quantity": int}, ...]}
    """
    logger.debug(f"Обновление записи selection_data={selection_data}")
    try:
        # Проверяем, существует ли запись UserSelection с таким user_id и check_uuid
        stmt = select(UserSelection).filter_by(user_id=user_id, check_uuid=check_uuid)
        result = await session.execute(stmt)
        user_selection = result.scalars().first()

        # Извлекаем selected_items из selection_data
        selected_items = selection_data.get("selected_items", [])

        if user_selection:
            # Если запись существует, удаляем старые SelectedItem и добавляем новые
            await session.execute(
                delete(SelectedItem).where(
                    SelectedItem.user_selection_user_id == user_id,
                    SelectedItem.user_selection_check_uuid == check_uuid
                )
            )
            logger.debug(f"Удалены старые записи SelectedItem для user_id={user_id}, check_uuid={check_uuid}")
        else:
            # Если записи нет, создаём новую UserSelection
            user_selection = UserSelection(
                user_id=user_id,
                check_uuid=check_uuid
            )
            session.add(user_selection)
            logger.debug(f"Создана новая запись UserSelection для user_id={user_id}, check_uuid={check_uuid}")

        # Добавляем новые записи в SelectedItem
        for item in selected_items:
            item_id = item.get("item_id")
            quantity = item.get("quantity")
            if item_id is not None and quantity is not None:
                selected_item = SelectedItem(
                    user_selection_user_id=user_id,
                    user_selection_check_uuid=check_uuid,
                    item_id=item_id,
                    quantity=quantity
                )
                session.add(selected_item)
            else:
                logger.warning(f"Некорректные данные в selected_items: {item}")

        # Сохраняем изменения в базе данных
        await session.commit()

        # После успешного сохранения добавляем данные в Redis (в формате JSON для совместимости)
        redis_key = f"user_selection:{user_id}:{check_uuid}"
        await redis_client.set(redis_key, json.dumps(selection_data), expire=REDIS_EXPIRATION)
        logger.debug(f"Данные сохранены в Redis для ключа {redis_key}")

    except Exception as e:
        logger.error(f"Ошибка добавления или обновления записи: {e}")
        raise Exception(f"Ошибка при обновлении данных пользователя: {str(e)}")


async def get_user_selection_by_user(session: AsyncSession, user_id: int, check_uuid: str):
    """
    Получить запись UserSelection для указанного пользователя и чека.

    :param session: Асинхронная сессия SQLAlchemy
    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :return: Объект UserSelection или None, если запись не найдена
    """
    stmt = select(UserSelection).filter_by(user_id=user_id, check_uuid=check_uuid)
    result = await session.execute(stmt)
    user_selection = result.scalars().first()
    return user_selection


async def get_user_selection_by_check_uuid(session: AsyncSession, check_uuid: str):
    """
    Получить данные о пользователях и их выбранных элементах для указанного чека.

    :param session: Асинхронная сессия SQLAlchemy
    :param check_uuid: UUID чека
    :return: Кортеж (json участников, json выбранных элементов, список пользователей)
    """
    users = await get_users_by_check_uuid(session, check_uuid)
    logger.debug(f"Получили пользователей: {', '.join([str(user) for user in users])}")

    participants = []
    user_selections = []

    for user in users:
        redis_key = f"user_selection:{user.id}:{check_uuid}"

        # Пытаемся получить данные из Redis или БД
        selection_data = {}
        redis_data = await redis_client.get(redis_key)

        if redis_data:
            selection_data = json.loads(redis_data)
            logger.debug(f"selection_data from redis: {selection_data}")
        else:
            # Получаем UserSelection и связанные SelectedItem
            user_selection = await get_user_selection_by_user(session, user.id, check_uuid)
            logger.debug(f"user_selection: {user_selection}")
            if user_selection:
                # Формируем selection_data из отношения selected_items
                selection_data = {
                    "selected_items": [
                        {"item_id": item.item_id, "quantity": item.quantity}
                        for item in user_selection.selected_items
                    ]
                }
                logger.debug(f"selection_data from DB: {selection_data}")
                # Сохраняем в Redis для последующих запросов
                await redis_client.set(redis_key, json.dumps(selection_data), expire=REDIS_EXPIRATION)

        logger.debug(f"Получили selection_data: {selection_data}")

        # Создаём структуру для каждого участника
        participant = {
            "user_id": user.id,
            "nickname": user.profile.nickname,
            "avatar_url": user.profile.avatar_url,
        }
        all_user_selection = {
            "user_id": user.id,
            "selected_items": [
                {"item_id": item["item_id"], "quantity": item["quantity"]}
                for item in selection_data.get("selected_items", [])
            ]
        }

        participants.append(participant)
        user_selections.append(all_user_selection)

    logger.debug(f"Получили participants: {participants}")

    return json.dumps(participants), json.dumps(user_selections), users


async def delete_item_from_user_selections(session: AsyncSession, check_uuid: str, item_id: int):
    """
    Удаляет элемент с заданным item_id из выбранных элементов всех пользователей для указанного чека.

    :param session: Асинхронная сессия SQLAlchemy
    :param check_uuid: UUID чека
    :param item_id: ID элемента чека для удаления
    """
    # Получаем всех пользователей, связанных с чеком (предполагается, что функция get_users_by_check_uuid уже существует)
    users = await get_users_by_check_uuid(session, check_uuid)

    for user in users:
        # Проверяем, есть ли запись UserSelection для данного пользователя и чека
        stmt = select(UserSelection).filter_by(user_id=user.id, check_uuid=check_uuid)
        result = await session.execute(stmt)
        user_selection = result.scalars().first()

        if user_selection:
            # Удаляем запись из SelectedItem, соответствующую user_id, check_uuid и item_id
            delete_stmt = delete(SelectedItem).where(
                SelectedItem.user_selection_user_id == user.id,
                SelectedItem.user_selection_check_uuid == check_uuid,
                SelectedItem.item_id == item_id
            )
            result = await session.execute(delete_stmt)

            # Проверяем, была ли удалена запись (rowcount > 0)
            if result.rowcount > 0:
                logger.debug(f"Удалён элемент item_id={item_id} для user_id={user.id}, check_uuid={check_uuid}")
                await session.commit()
            else:
                logger.debug(f"Элемент item_id={item_id} не найден для user_id={user.id}, check_uuid={check_uuid}")
        else:
            logger.debug(f"UserSelection не найдена для user_id={user.id}, check_uuid={check_uuid}")
