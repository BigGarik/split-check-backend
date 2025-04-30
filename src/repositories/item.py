import json
import logging
import math
from typing import Dict, Any

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.config import REDIS_EXPIRATION
from src.models import Check, CheckItem
from src.redis import redis_client
from src.repositories.user_selection import delite_item_from_user_selections
from src.schemas import EditItemRequest
from src.utils.check import recalculate_check_totals, to_int, to_float

logger = logging.getLogger(__name__)


async def get_items_by_check_uuid(session: AsyncSession, check_uuid: str) -> list[CheckItem]:
    """
    Получение всех позиций чека по его UUID.

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека

    Returns:
        list[CheckItem]: Список объектов CheckItem с атрибутами id, name, quantity, sum

    Raises:
        Exception: Если чек не найден или произошла ошибка при запросе
    """
    try:
        # Получаем все позиции чека
        stmt = select(CheckItem).where(CheckItem.check_uuid == check_uuid)
        result = await session.execute(stmt)
        items = result.scalars().all()

        # Если позиций нет, проверяем существование чека
        if not items:
            stmt_check = select(Check).where(Check.uuid == check_uuid)
            result_check = await session.execute(stmt_check)
            check = result_check.scalars().first()
            if not check:
                raise Exception(f"Check with UUID {check_uuid} not found")

        logger.debug(f"Retrieved {len(items)} items for check {check_uuid}")

        return list(items)  # Возвращаем список объектов CheckItem

    except Exception as e:
        logger.error(f"Error retrieving items for check {check_uuid}: {e}")
        raise


async def remove_item_from_check(session: AsyncSession, check_uuid: str, item_id: int) -> dict:
    """
    Удаление элемента из чека по его id

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека
        item_id: int - ID позиции для удаления

    Returns:
        dict: Удаленная позиция

    Raises:
        Exception: Если чек не найден или позиция не найдена
    """

    # Получаем чек
    stmt = select(Check).where(Check.uuid == check_uuid)
    result = await session.execute(stmt)
    check = result.scalars().first()

    if not check:
        raise Exception("Check not found")

    # Находим позицию для удаления
    items = check.check_data.get("items", [])
    item_index = None
    removed_item = None

    for index, item in enumerate(items):
        if item["id"] == item_id:
            item_index = index
            removed_item = item
            break

    if item_index is None:
        raise Exception(f"ItemRequest with id {item_id} not found in check")

    # Удаляем позицию
    items.pop(item_index)

    # Переназначаем id для оставшихся позиций
    for index, item in enumerate(items, start=1):
        item["id"] = index

    check.check_data["items"] = items

    # Пересчитываем все поля
    check.check_data = recalculate_check_totals(check.check_data)

    # Помечаем check_data как измененное
    flag_modified(check, "check_data")
    await session.commit()
    await session.refresh(check)

    # Кладем новые данные чека в Redis
    redis_key = f"check_uuid:{check_uuid}"
    check_data = check.check_data
    logger.debug(f"Данные чека найдены в базе данных для UUID: {check_uuid}")

    # Кэшируем данные чека в Redis для будущих обращений
    await redis_client.set(redis_key, json.dumps(check_data), expire=REDIS_EXPIRATION)

    await delite_item_from_user_selections(session, check_uuid, item_id)

    return removed_item


async def add_item_to_check(session: AsyncSession, check_uuid: str, item_data: dict) -> dict:
    """Добавление элемента в чек и возврат обновленного объекта Check"""
    try:
        # Проверяем существование чека
        stmt = select(Check).where(Check.uuid == check_uuid)
        result = await session.execute(stmt)
        check = result.scalars().first()
        if not check:
            raise Exception(f"Check with UUID {check_uuid} not found")

        logger.debug(f"Adding item to check {check_uuid}: {item_data}")

        # Извлекаем данные элемента
        item_id = item_data.get("id")

        if item_id is None:
            # Получаем максимальный item_id в данном чеке
            stmt = select(func.max(CheckItem.item_id)).where(CheckItem.check_uuid == check_uuid)
            result = await session.execute(stmt)
            max_item_id = result.scalar() or 0
            item_id = max_item_id + 1
        else:
            item_id = to_int(item_id)

        name = item_data.get("name")
        float_quantity = to_float(item_data.get("quantity"))
        if float_quantity.is_integer():
            quantity = int(float_quantity)
        else:
            name = f"{name} {float_quantity}"
            # Округляем в большую сторону
            quantity = math.ceil(float_quantity)
        sum_value = to_float(item_data.get("sum"))

        if item_id is None or quantity is None or sum_value is None or not name:
            raise ValueError(f"Invalid item data for check {check_uuid}: {item_data}")

        # Создаем новый элемент чека
        new_item = CheckItem(
            check_uuid=check_uuid,
            item_id=item_id,
            name=name,
            quantity=quantity,
            sum=sum_value
        )
        session.add(new_item)
        await session.flush()


        logger.debug(f"Item added to check {check_uuid}: {item_data}")

        # Возвращаем данные добавленного элемента
        item_response = {
            "id": new_item.item_id,
            "name": new_item.name,
            "quantity": new_item.quantity,
            "sum": new_item.sum
        }

        await session.commit()
        return item_response

    except Exception as e:
        await session.rollback()
        logger.error(f"Error adding item to check {check_uuid}: {e}")
        raise


async def edit_item_in_check(
    session: AsyncSession,
    check_uuid: str,
    item_data: EditItemRequest
) -> Dict[str, Any]:
    """Редактирование элемента в чеке
    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека
        item_data: EditItemRequest - данные для редактирования

    Returns:
        dict: Обновленные данные check_data чека

    Raises:
        Exception: Если чек не найден или позиция не найдена
    """
    logger.debug(f"Edit item in check: {item_data}")

    # Поиск в базе данных, если нет в Redis
    stmt = select(Check).filter_by(uuid=check_uuid)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()

    # Проверяем, существует ли item_id в check_data
    item_found = False
    for item in check.check_data.get("items", []):
        logger.debug(f"Item in check: {item}")

        if item.get("id") == item_data.id:
            # Обновляем поля, если они были переданы
            if item_data.name is not None:
                item["name"] = item_data.name
            if item_data.quantity is not None:
                item["quantity"] = item_data.quantity
            if item_data.sum is not None:
                item["sum"] = item_data.sum
            item["price"] = item["sum"] / item["quantity"]
            item_found = True
            break

    if not item_found:
        raise HTTPException(status_code=404, detail="Item not found in check")

    # Пересчитываем все поля
    check_data = recalculate_check_totals(check.check_data)

    # Явно помечаем атрибут как измененный
    flag_modified(check, "check_data")

    # Сохраняем изменения в базе данных
    await session.commit()
    await session.refresh(check)

    # Кладем новые данные чека в Redis
    redis_key = f"check_uuid:{check_uuid}"
    check_data = check_data
    logger.debug(f"Данные чека найдены в базе данных для UUID: {check_uuid}")

    # Кэшируем данные чека в Redis для будущих обращений
    await redis_client.set(redis_key, json.dumps(check_data), expire=REDIS_EXPIRATION)

    await delite_item_from_user_selections(session, check_uuid, item_data.id)

    logger.debug(f"Обновленные данные check: {check_data}")
    return check_data


# refac
async def update_item_quantity(session: AsyncSession, check_uuid: str, item_id: int, quantity: int):
    try:
        # 1. Найти нужный элемент по item_id и check_uuid
        stmt = select(CheckItem).where(
            CheckItem.check_uuid == check_uuid,
            CheckItem.item_id == item_id
        )
        result = await session.execute(stmt)
        item: CheckItem = result.scalar_one_or_none()

        if not item:
            logger.error(f"Элемент с item_id={item_id} не найден в чеке {check_uuid}")
            raise ValueError("Item not found")

        # 2. Обновить quantity
        if quantity <= 0:
            raise ValueError("Quantity must be > 0")

        item.quantity = quantity

    except Exception as e:
        logger.error(f"Ошибка при обновлении количества элемента: {e}")
        raise e
