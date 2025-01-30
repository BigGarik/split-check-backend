import json
from typing import Dict, Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.config.settings import settings
from src.models import Check
from src.redis import redis_client
from src.schemas import AddItemRequest, EditItemRequest
from src.utils.check import recalculate_check_totals


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
    await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)

    return removed_item


async def add_item_to_check(session: AsyncSession, check_uuid: str, item_data: AddItemRequest) -> dict:
    """Добавление элемента в чек и возврат обновленного объекта Check"""

    stmt = select(Check).where(Check.uuid == check_uuid)
    result = await session.execute(stmt)
    check = result.scalars().first()
    if not check:
        raise Exception("Check not found")
    logger.debug(f"Add item to check: {item_data}")

    # Создаем новый item
    new_item = {
        "id": len(check.check_data.get("items", [])) + 1,
        "name": item_data.name,
        "quantity": item_data.quantity,
        "price": item_data.sum / item_data.quantity,
        "sum": item_data.sum
    }

    # Инициализируем items если их нет
    if "items" not in check.check_data:
        check.check_data["items"] = []

    # Добавляем новый item
    check.check_data["items"].append(new_item)

    # Добавляем/обновляем дополнительные поля если их нет
    if "date" not in check.check_data:
        from datetime import datetime
        current_time = datetime.now()
        check.check_data["date"] = current_time.strftime("%d.%m.%Y")
        check.check_data["time"] = current_time.strftime("%H:%M")

    # Убеждаемся, что все необходимые поля присутствуют
    default_fields = {
        "waiter": "",
        "restaurant": "",
        "order_number": "",
        "table_number": ""
    }

    for field, default_value in default_fields.items():
        if field not in check.check_data:
            check.check_data[field] = default_value

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
    await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)

    return new_item


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
    await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)

    logger.debug(f"Обновленные данные check: {check_data}")
    return check_data


async def update_item_quantity(session: AsyncSession, check_uuid: str, item_id: int, quantity: int):
    try:
        # Проверка существования чека
        check = await session.get(Check, check_uuid)
        if not check:
            logger.warning(f"Чек с UUID {check_uuid} не найден.")
            raise ValueError("Check not found")

        # Обновление количества, если элемент найден
        updated = False
        for item in check.check_data.get("items", []):
            if item["id"] == item_id:
                item["quantity"] = quantity
                item["price"] = item["sum"] / item["quantity"]
                updated = True
                logger.debug(f"Обновлено количество для элемента {item_id} в чеке {check_uuid} на {quantity}")
                break

        if not updated:
            logger.warning(f"Элемент с ID {item_id} не найден в чеке {check_uuid}")
            raise ValueError("ItemRequest not found in check data")

        # Явное обновление поля check_data
        flag_modified(check, "check_data")
        await session.commit()

        # Обновление кэша Redis, если данные изменены
        redis_key = f"check_uuid:{check_uuid}"
        await redis_client.set(redis_key, json.dumps(check.check_data), expire=settings.redis_expiration)
        logger.info(f"Данные чека {check_uuid} обновлены в Redis.")

    except Exception as e:
        logger.error(f"Ошибка при обновлении количества элемента: {e}")
        raise e
