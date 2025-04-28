import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Check, CheckItem

logger = logging.getLogger(__name__)


def to_float(value, default=None):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid float value: {value}, using default: {default}")
        return default


def to_int(value, default=None):
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid integer value: {value}, using default: {default}")
        return default


async def recalculate_check_totals(session: AsyncSession, check_uuid) -> None:
    """
    Пересчитывает subtotal и total для чека на основе текущих позиций и данных о сборах, налогах и скидках.

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека

    Raises:
        Exception: Если чек не найден
    """
    try:
        # Получаем чек
        stmt = select(Check).filter_by(uuid=check_uuid)
        result = await session.execute(stmt)
        check = result.scalar_one_or_none()
        if not check:
            raise Exception(f"Check with UUID {check_uuid} not found")

        # Получаем все позиции чека
        stmt = select(CheckItem).where(CheckItem.check_uuid == check_uuid)
        result = await session.execute(stmt)
        items = result.scalars().all()

        # Пересчитываем subtotal как сумму всех позиций
        new_subtotal = sum(item.sum for item in items)
        check.subtotal = new_subtotal

        # Получаем текущие значения сборов, налогов и скидок
        service_charge_amount = to_float(check.service_charge_amount, 0)
        vat_amount = to_float(check.vat_amount, 0)
        discount_amount = to_float(check.discount_amount, 0)

        # Пересчитываем total: subtotal + сборы + налоги - скидки
        new_total = new_subtotal + service_charge_amount + vat_amount - discount_amount
        check.total = new_total

        logger.debug(
            f"Recalculated totals for check {check_uuid}: "
            f"subtotal={new_subtotal}, total={new_total}"
        )

        # Обновляем объект в сессии (commit будет вызван в вызывающей функции)
        await session.flush()

    except Exception as e:
        logger.error(f"Error recalculating totals for check {check_uuid}: {e}")
        raise


# def recalculate_check_totals(check_data: dict) -> dict:
#     """Пересчет всех полей чека"""
#
#     # Пересчитываем subtotal (сумма всех items)
#     subtotal = sum(
#         item["sum"]  # * item["quantity"]
#         for item in check_data.get("items", [])
#     )
#     check_data["subtotal"] = subtotal
#
#     # Пересчитываем VAT если есть ставка
#     vat_rate = check_data.get("vat", {}).get("rate", 0)
#     if vat_rate:
#         vat_amount = (subtotal * vat_rate) / 100
#         check_data["vat"] = {
#             "rate": vat_rate,
#             "amount": round(vat_amount, 2)
#         }
#     else:
#         check_data["vat"] = {
#             "rate": 0,
#             "amount": 0
#         }
#
#     # Пересчитываем service charge если есть
#     service_charge = check_data.get("service_charge", {})
#     service_charge_name = service_charge.get("name", "")
#     if service_charge_name:
#         import re
#         if match := re.search(r'\((\d+)%\)', service_charge_name):
#             service_rate = float(match.group(1))
#             service_amount = (subtotal * service_rate) / 100
#             check_data["service_charge"] = {
#                 "name": service_charge_name,
#                 "amount": round(service_amount, 2)
#             }
#     else:
#         check_data["service_charge"] = {
#             "name": "",
#             "amount": 0
#         }
#
#     # Пересчитываем total (subtotal + vat + service charge)
#     total = (
#             check_data["subtotal"] +
#             check_data["vat"]["amount"] +
#             check_data["service_charge"]["amount"]
#     )
#     check_data["total"] = round(total, 2)
#
#     return check_data
