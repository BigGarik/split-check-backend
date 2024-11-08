from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.models import Check
from src.schemas import AddItemRequest, EditItemRequest
from src.utils.check import recalculate_check_totals
from src.utils.db import with_db_session


@with_db_session()
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
        raise Exception(f"Item with id {item_id} not found in check")

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

    return removed_item


@with_db_session()
async def add_item_to_check(session: AsyncSession, item_data: AddItemRequest) -> dict:
    """Добавление элемента в чек и возврат обновленного объекта Check"""

    stmt = select(Check).where(Check.uuid == item_data.uuid)
    result = await session.execute(stmt)
    check = result.scalars().first()
    if not check:
        raise Exception("Check not found")

    # Создаем новый item
    new_item = {
        "id": len(check.check_data.get("items", [])) + 1,
        "name": item_data.name,
        "quantity": item_data.quantity,
        "price": item_data.price
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

    return new_item


@with_db_session()
async def edit_item_in_check(session: AsyncSession, item_data: EditItemRequest):
    """Редактирование элемента в чеке
    Args:
        session: AsyncSession - сессия базы данных
        item_data: EditItemRequest - данные для редактирования

    Returns:
        dict: Обновленные данные check_data чека

    Raises:
        Exception: Если чек не найден или позиция не найдена"""
    logger.debug(f"Edit item in check: {item_data}")

    # Получаем чек по UUID
    stmt = select(Check).where(Check.uuid == item_data.uuid)
    result = await session.execute(stmt)
    check = result.scalars().first()

    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

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
            if item_data.price is not None:
                item["price"] = item_data.price
            item_found = True
            break

    if not item_found:
        raise HTTPException(status_code=404, detail="Item not found in check data")

    # Пересчитываем все поля
    check.check_data = recalculate_check_totals(check.check_data)

    # Явно помечаем атрибут как измененный
    flag_modified(check, "check_data")

    # Сохраняем изменения в базе данных
    await session.commit()
    await session.refresh(check)

    logger.debug(f"Обновленные данные check: {check.check_data}")
    return check.check_data
