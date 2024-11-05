from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.database import with_db_session
from app.models import Check
from app.schemas import AddItemRequest


def recalculate_check_totals(check_data: dict) -> dict:
    """Пересчет всех полей чека"""

    # Пересчитываем subtotal (сумма всех items)
    subtotal = sum(
        item["price"]  # * item["quantity"]
        for item in check_data.get("items", [])
    )
    check_data["subtotal"] = subtotal

    # Пересчитываем VAT если есть ставка
    vat_rate = check_data.get("vat", {}).get("rate", 0)
    if vat_rate:
        vat_amount = (subtotal * vat_rate) / 100
        check_data["vat"] = {
            "rate": vat_rate,
            "amount": round(vat_amount, 2)
        }
    else:
        check_data["vat"] = {
            "rate": 0,
            "amount": 0
        }

    # Пересчитываем service charge если есть
    service_charge = check_data.get("service_charge", {})
    service_charge_name = service_charge.get("name", "")
    if service_charge_name:
        import re
        if match := re.search(r'\((\d+)%\)', service_charge_name):
            service_rate = float(match.group(1))
            service_amount = (subtotal * service_rate) / 100
            check_data["service_charge"] = {
                "name": service_charge_name,
                "amount": round(service_amount, 2)
            }
    else:
        check_data["service_charge"] = {
            "name": "",
            "amount": 0
        }

    # Пересчитываем total (subtotal + vat + service charge)
    total = (
            check_data["subtotal"] +
            check_data["vat"]["amount"] +
            check_data["service_charge"]["amount"]
    )
    check_data["total"] = round(total, 2)

    return check_data


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
async def add_item_to_check(session: AsyncSession, item: AddItemRequest) -> dict:
    """Добавление элемента в чек и возврат обновленного объекта Check"""

    stmt = select(Check).where(Check.uuid == item.uuid)
    result = await session.execute(stmt)
    check = result.scalars().first()
    if not check:
        raise Exception("Check not found")

    # Создаем новый item
    new_item = {
        "id": len(check.check_data.get("items", [])) + 1,
        "name": item.name,
        "quantity": item.quantity,
        "price": item.price
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
