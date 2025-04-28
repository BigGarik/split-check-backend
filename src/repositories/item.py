import json
import logging
from typing import Dict, Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from src.config import REDIS_EXPIRATION
from src.models import Check, CheckItem
from src.redis import redis_client
from src.repositories.user_selection import delete_item_from_user_selections
from src.schemas import AddItemRequest, EditItemRequest
from src.utils.check import to_int, to_float, recalculate_check_totals

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
    Удаление элемента из чека по его id из таблицы check_items, без изменения check_data["items"].

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека
        item_id: int - ID позиции для удаления

    Returns:
        dict: Удаленная позиция в формате {"id": int, "name": str, "quantity": int, "sum": float}

    Raises:
        Exception: Если чек или позиция не найдены
    """
    try:
        # Получаем чек
        stmt = select(Check).where(Check.uuid == check_uuid)
        result = await session.execute(stmt)
        check = result.scalars().first()

        if not check:
            raise Exception(f"Check with UUID {check_uuid} not found")

        # Находим позицию для удаления в таблице check_items
        stmt_item = select(CheckItem).where(
            CheckItem.check_uuid == check_uuid,
            CheckItem.item_id == item_id
        )
        result_item = await session.execute(stmt_item)
        item = result_item.scalars().first()

        if not item:
            raise Exception(f"Item with ID {item_id} not found in check {check_uuid}")

        # Сохраняем данные удалённой позиции
        removed_item = {
            "id": item.item_id,
            "name": item.name,
            "quantity": item.quantity,
            "sum": float(item.sum)
        }

        # Удаляем позицию из таблицы check_items
        await session.delete(item)
        await session.flush()

        # Пересчитываем subtotal и total в объекте Check
        await recalculate_check_totals(session, check_uuid)

        # Удаляем позицию из user_selections
        await delete_item_from_user_selections(session, check_uuid, item_id)

        # Фиксируем изменения в базе данных
        await session.commit()
        await session.refresh(check)

        # Кэшируем данные чека в Redis (check_data остаётся оригинальным)
        redis_key = f"check_uuid:{check_uuid}"
        check_data = check.check_data  # Оригинальный check_data без изменений
        logger.debug(f"Updated check data for UUID {check_uuid} cached in Redis: {check_data}")
        await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)

        logger.debug(f"Item {item_id} removed from check {check_uuid}: {removed_item}")
        return removed_item

    except Exception as e:
        await session.rollback()
        logger.error(f"Error removing item {item_id} from check {check_uuid}: {e}")
        raise
    # # Получаем чек
    # stmt = select(Check).where(Check.uuid == check_uuid)
    # result = await session.execute(stmt)
    # check = result.scalars().first()
    #
    # if not check:
    #     raise Exception("Check not found")
    #
    # # Находим позицию для удаления
    # items = check.check_data.get("items", [])
    # item_index = None
    # removed_item = None
    #
    # for index, item in enumerate(items):
    #     if item["id"] == item_id:
    #         item_index = index
    #         removed_item = item
    #         break
    #
    # if item_index is None:
    #     raise Exception(f"ItemRequest with id {item_id} not found in check")
    #
    # # Удаляем позицию
    # items.pop(item_index)
    #
    # # Переназначаем id для оставшихся позиций
    # for index, item in enumerate(items, start=1):
    #     item["id"] = index
    #
    # check.check_data["items"] = items
    #
    # # Пересчитываем все поля
    # check.check_data = recalculate_check_totals(check.check_data)
    #
    # # Помечаем check_data как измененное
    # flag_modified(check, "check_data")
    # await session.commit()
    # await session.refresh(check)
    #
    # # Кладем новые данные чека в Redis
    # redis_key = f"check_uuid:{check_uuid}"
    # check_data = check.check_data
    # logger.debug(f"Данные чека найдены в базе данных для UUID: {check_uuid}")
    #
    # # Кэшируем данные чека в Redis для будущих обращений
    # await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
    #
    # await delite_item_from_user_selections(session, check_uuid, item_id)
    #
    # return removed_item


async def add_item_to_check(session: AsyncSession, check_uuid: str, item_data: AddItemRequest) -> dict:
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
        item_id = to_int(item_data.get("id"))
        quantity = to_int(item_data.get("quantity"))
        sum_value = to_float(item_data.get("sum"))
        name = item_data.get("name")

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

        # Пересчитываем subtotal и total в объекте Check
        await recalculate_check_totals(session, check_uuid)

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
    #
    #     # Создаем новый item
    #     new_item = {
    #         "id": len(check.check_data.get("items", [])) + 1,
    #         "name": item_data.name,
    #         "quantity": item_data.quantity,
    #         "price": item_data.sum / item_data.quantity,
    #         "sum": item_data.sum
    #     }
    #     logger.debug(f"New item: {new_item}")
    #
    #     # Инициализируем items если их нет
    #     if "items" not in check.check_data:
    #         check.check_data["items"] = []
    #
    #     # Добавляем новый item
    #     check.check_data["items"].append(new_item)
    #
    #     # Добавляем/обновляем дополнительные поля если их нет
    #     if "date" not in check.check_data:
    #         from datetime import datetime
    #         current_time = datetime.now()
    #         check.check_data["date"] = current_time.strftime("%d.%m.%Y")
    #         check.check_data["time"] = current_time.strftime("%H:%M")
    #
    #     # Убеждаемся, что все необходимые поля присутствуют
    #     default_fields = {
    #         "waiter": "",
    #         "restaurant": "",
    #         "order_number": "",
    #         "table_number": ""
    #     }
    #
    #     for field, default_value in default_fields.items():
    #         if field not in check.check_data:
    #             check.check_data[field] = default_value
    #
    #     # Пересчитываем все поля
    #     check.check_data = recalculate_check_totals(check.check_data)
    #
    #     # Помечаем check_data как измененное
    #     flag_modified(check, "check_data")
    #     await session.commit()
    #     await session.refresh(check)
    #
    #     # Кладем новые данные чека в Redis
    #     redis_key = f"check_uuid:{check_uuid}"
    #     check_data = check.check_data
    #     logger.debug(f"Данные чека найдены в базе данных для UUID: {check_uuid}")
    #
    #     # Кэшируем данные чека в Redis для будущих обращений
    #     await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
    #
    #     return new_item
    # except Exception as e:
    #     logger.error(f"Error adding item to check: {e}")
    #     raise


async def edit_item_in_check(session: AsyncSession, check_uuid: str, item_data: EditItemRequest) -> dict:
    """Редактирование элемента в чеке.

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека
        item_data: EditItemRequest - данные для редактирования (id, name, quantity, sum)

    Returns:
        dict: Обновленные данные чека

    Raises:
        HTTPException: Если чек или элемент не найдены
    """
    logger.debug(f"Редактирование элемента в чеке: {item_data}")

    # Поиск чека
    check = await session.get(Check, check_uuid)
    if not check:
        raise HTTPException(status_code=404, detail="Чек не найден")

    # Поиск элемента чека
    stmt = select(CheckItem).filter_by(check_uuid=check_uuid, item_id=item_data.id)
    result = await session.execute(stmt)
    check_item = result.scalar_one_or_none()

    if not check_item:
        raise HTTPException(status_code=404, detail="Элемент не найден в чеке")

    # Обновление полей, если они переданы
    if item_data.name is not None:
        check_item.name = item_data.name
    if item_data.quantity is not None:
        check_item.quantity = item_data.quantity
    if item_data.sum is not None:
        check_item.sum = item_data.sum

    # Сохранение изменений
    await session.commit()
    await session.refresh(check_item)

    # Пересчитываем subtotal и total в объекте Check
    if item_data.sum is not None:
        await recalculate_check_totals(session, check_uuid)

    await session.commit()

    # Синхронизация с таблицей SelectedItem
    await delete_item_from_user_selections(session, check_uuid, item_data.id)



    logger.debug(f"Обновленные данные чека: {check}")
    return {"uuid": check.uuid, "subtotal": check.subtotal, "total": check.total}


async def update_item_quantity(session: AsyncSession, check_uuid: str, item_id: int, quantity: int) -> None:
    """Обновление количества элемента в чеке.

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека
        item_id: int - ID элемента чека
        quantity: int - Новое количество

    Raises:
        ValueError: Если чек или элемент не найдены
    """
    # Поиск чека
    check = await session.get(Check, check_uuid)
    if not check:
        logger.warning(f"Чек с UUID {check_uuid} не найден")
        raise ValueError("Чек не найден")

    # Поиск элемента чека
    stmt = select(CheckItem).filter_by(check_uuid=check_uuid, item_id=item_id)
    result = await session.execute(stmt)
    check_item = result.scalar_one_or_none()

    if not check_item:
        logger.warning(f"Элемент с ID {item_id} не найден в чеке {check_uuid}")
        raise ValueError("Элемент не найден в чеке")

    # Обновление количества
    check_item.quantity = quantity
    await session.commit()

    # Синхронизация с таблицей SelectedItem
    await delete_item_from_user_selections(session, check_uuid, item_id)

    logger.info(f"Обновлено количество для элемента {item_id} в чеке {check_uuid}")
