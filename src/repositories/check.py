import json
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy import select, insert, delete, func, and_, update, exists
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from starlette.exceptions import HTTPException

from src.config import REDIS_EXPIRATION
from src.models import Check, user_check_association, User, UserSelection
from src.redis import redis_client
from src.repositories.item import add_item_to_check, get_items_by_check_uuid
from src.schemas import CheckListResponse
from src.utils.check import to_float

logger = logging.getLogger(__name__)


async def get_check_by_uuid(session: AsyncSession, check_uuid: str) -> Optional[Check]:
    stmt = select(Check).filter_by(uuid=check_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_check_data_from_database(session: AsyncSession, check_uuid: str) -> dict:
    """
    Получение данных чека из базы данных в формате check_data.

    Args:
        session: AsyncSession - сессия базы данных
        check_uuid: str - UUID чека

    Returns:
        dict: Данные чека в формате JSON, включая все поля и позиции

    Raises:
        Exception: Если чек не найден
    """
    try:
        check = await get_check_by_uuid(session, check_uuid)
        if not check:
            raise Exception(f"Check with UUID {check_uuid} not found")

        # Получаем все позиции чека
        items = await get_items_by_check_uuid(session, check_uuid)

        # Формируем check_data
        check_data = {
            "uuid": check.uuid,
            "name": check.name,
            "date": check.created_at.strftime("%d.%m.%Y"),
            "restaurant": check.restaurant,
            # "address": check.address,
            # "phone": check.phone,
            # "table_number": check.table_number,
            # "order_number": check.order_number,
            # "date": check.date,
            # "time": check.time,
            # "waiter": check.waiter,
            "subtotal": float(check.subtotal) if check.subtotal is not None else 0.0,
            "total": float(check.total) if check.total is not None else 0.0,
            "currency": check.currency,
            "author_id": check.author_id,
            "status": check.status.value,
            "error_comment": check.error_comment,
            "service_charge": None if check.service_charge_name is None and check.service_charge_amount is None else {
                "name": check.service_charge_name,
                "percentage": float(
                    check.service_charge_percentage) if check.service_charge_percentage is not None else None,
                "amount": float(check.service_charge_amount) if check.service_charge_amount is not None else None
            },
            "vat": None if check.vat_rate is None and check.vat_amount is None else {
                "rate": float(check.vat_rate) if check.vat_rate is not None else None,
                "amount": float(check.vat_amount) if check.vat_amount is not None else None
            },
            "discount": None if check.discount_percentage is None and check.discount_amount is None else {
                "percentage": float(check.discount_percentage) if check.discount_percentage is not None else None,
                "amount": float(check.discount_amount) if check.discount_amount is not None else None
            },
            "items": [
                {
                    "id": item.item_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "sum": float(item.sum)
                }
                for item in items
            ]
        }

        logger.debug(f"Подготовлены check_data для чека {check_uuid}")

        redis_key = f"check_uuid:{check_uuid}"

        # Кэширование в Redis
        await redis_client.set(
            redis_key,
            json.dumps(check_data),
            expire=REDIS_EXPIRATION
        )

        return check_data

    except Exception as e:
        logger.error(f"Error retrieving check_data for check {check_uuid}: {e}")
        raise


# @with_db_session()
# async def get_check_data_by_uuid(session: AsyncSession, check_uuid: str) -> Dict[str, Any]:
#     """
#     Получение данных чека по UUID с использованием кэширования в Redis.
#
#     Args:
#         session: AsyncSession - сессия базы данных
#         check_uuid: str - UUID чека
#
#     Returns:
#         Dict[str, Any]: Данные чека
#
#     Raises:
#         HTTPException: Если чек не найден
#         Exception: При ошибках доступа к БД или Redis
#     """
#     redis_key = f"check_uuid:{check_uuid}"
#
#     try:
#         # Попытка получить данные из Redis
#         cached_data = await redis_client.get(redis_key)
#         if cached_data:
#             check_data = json.loads(cached_data)
#             logger.debug(f"Получены данные чека из Redis: {check_uuid}")
#             return check_data
#
#         # Поиск в базе данных, если нет в Redis
#         stmt = select(Check).filter_by(uuid=check_uuid)
#         result = await session.execute(stmt)
#         check = result.scalar_one_or_none()
#
#         if not check:
#             logger.warning(f"Чек не найден: {check_uuid}")
#             raise HTTPException(status_code=404, detail="Check not found")
#
#         # Кэширование в Redis
#         await redis_client.set(
#             redis_key,
#             json.dumps(check.check_data),
#             expire=settings.redis_expiration
#         )
#
#         logger.debug(f"Данные чека получены из БД: {check_uuid}")
#         return check.check_data
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Ошибка при получении данных чека {check_uuid}: {str(e)}")
#         raise HTTPException(status_code=500, detail="Internal server error")


# async def update_check_data_to_database(session: AsyncSession, check_uuid: str, check_data: dict):
#     check = await get_check_by_uuid(session, check_uuid)
#     if not check:
#         raise HTTPException(status_code=404, detail="Check not found")
#
#     # Обновляем данные чека
#     check.check_data = check_data
#     flag_modified(check, "check_data")
#     await session.commit()


async def edit_check_name_to_database(session: AsyncSession, user_id: int, check_uuid: str, check_name: str) -> str:
    """
    Изменяет имя чека в базе данных, если пользователь имеет право доступа.

    :param session: AsyncSession для взаимодействия с базой данных
    :param user_id: ID пользователя, выполняющего запрос
    :param check_uuid: UUID чека
    :param check_name: Новое имя для чека
    :return: Статус операции
    """
    try:
        # Проверка, связан ли пользователь с чеком
        stmt_check_access = (
            select(exists().where(
                (user_check_association.c.user_id == user_id) &
                (user_check_association.c.check_uuid == check_uuid)
            ))
        )
        result = await session.execute(stmt_check_access)
        has_access = result.scalar()

        if not has_access:
            return "Access denied: User is not associated with this check."

        # Обновление имени чека
        stmt_update_name = (
            update(Check)
            .where(Check.uuid == check_uuid)
            .values(name=check_name, updated_at=datetime.now())
            .execution_options(synchronize_session="fetch")
        )
        result = await session.execute(stmt_update_name)

        if result.rowcount == 0:
            return "Check not found."

        await session.commit()

        return "Check name updated successfully."

    except NoResultFound:
        raise ValueError("Чек не найден или у пользователя нет доступа.")
    except Exception as e:
        await session.rollback()
        raise ValueError(f"Ошибка при обновлении имени чека: {e}")


async def edit_check_status_to_database(session: AsyncSession, user_id: int, check_uuid: str, check_status: str) -> str:
    """
    Изменяет статус чека в базе данных.

    :param session: AsyncSession для взаимодействия с базой данных
    :param user_id: ID пользователя, выполняющего запрос
    :param check_uuid: UUID чека
    :param check_status: Новый статус чека (из перечисления StatusEnum)
    :return: Статус операции
    """
    # Проверка, связан ли пользователь с чеком
    stmt_check_access = (
        select(exists().where(
            (user_check_association.c.user_id == user_id) &
            (user_check_association.c.check_uuid == check_uuid)
        ))
    )
    result = await session.execute(stmt_check_access)
    has_access = result.scalar()

    if not has_access:
        return "Access denied: User is not associated with this check."

    # Обновление статус чека
    stmt_update_name = (
        update(Check)
        .where(Check.uuid == check_uuid)
        .values(status=check_status, updated_at=datetime.now())
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(stmt_update_name)

    if result.rowcount == 0:
        return "Check not found."

    await session.commit()
    return "Check status updated successfully."


async def add_check_to_database(
        session: AsyncSession,
        check_uuid: str,
        user_id: int,
        check_data: dict
) -> None:
    """
        Создает новый чек в базе данных, заполняет все поля, добавляет позиции чека,
        устанавливает связь с пользователем.

        Функция выполняет следующие операции:
        1. Создает новую запись в таблице checks с заполнением всех полей из check_data
        2. Добавляет позиции чека из check_data["items"] в таблицу check_items через add_item_to_check
        3. Устанавливает пользователя как автора чека
        4. Создает связь между пользователем и чеком в таблице ассоциаций

        Args:
            session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с БД
            check_uuid (str): Уникальный идентификатор создаваемого чека
            user_id (int): ID пользователя, который создает чек
            check_data (dict): Данные чека для сохранения в формате JSON

        Raises:
            SQLAlchemyError: При ошибках работы с базой данных
            Exception: При любых других непредвиденных ошибок
        """
    try:
        # Создаем новый чек с указанием автора и заполнением всех полей
        new_check = Check(
            uuid=check_uuid,
            check_data=check_data,
            author_id=user_id,
            restaurant=check_data.get("restaurant"),
            address=check_data.get("address"),
            phone=check_data.get("phone"),
            table_number=check_data.get("table_number"),
            order_number=check_data.get("order_number"),
            date=check_data.get("date"),
            time=check_data.get("time"),
            waiter=check_data.get("waiter"),
            subtotal=to_float(check_data.get("subtotal"), 0),
            total=to_float(check_data.get("total"), 0),
            currency=check_data.get("currency")
        )

        # Сервисный сбор
        service_charge = check_data.get("service_charge")
        if service_charge is not None:
            new_check.service_charge_name = service_charge.get("name")
            new_check.service_charge_percentage = to_float(service_charge.get("percentage"))
            new_check.service_charge_amount = to_float(service_charge.get("amount"))

        # НДС
        vat = check_data.get("vat")
        if vat is not None:
            new_check.vat_rate = to_float(vat.get("rate"))
            new_check.vat_amount = to_float(vat.get("amount"))

        # Скидка
        discount = check_data.get("discount")
        if discount is not None:
            new_check.discount_name = discount.get("name")
            new_check.discount_percentage = to_float(discount.get("percentage"))
            new_check.discount_amount = to_float(discount.get("amount"))

        session.add(new_check)
        await session.flush()

        # Добавляем позиции чека из check_data["items"] через add_item_to_check
        items_added = []
        for item in check_data.get("items", []):
            item_response = await add_item_to_check(session, check_uuid, item)
            items_added.append(item_response)

        # Создаем связь между пользователем и чеком
        stmt = insert(user_check_association).values(
            user_id=user_id,
            check_uuid=check_uuid
        )
        await session.execute(stmt)

        # Валидация данных
        error_comments = []

        # 1. Проверяем сумму всех позиций против subtotal
        items_total = sum(item["sum"] for item in items_added)
        subtotal = to_float(check_data.get("subtotal"), 0)
        if abs(items_total - subtotal) > 0.01:  # Допускаем погрешность 0.01 из-за float
            error_comments.append(
                f"Sum of items ({items_total}) does not match subtotal ({subtotal})"
            )

        # 2. Проверяем total = subtotal + service_charge_amount + vat_amount - discount_amount
        service_charge_amount = to_float(service_charge.get("amount") if service_charge else 0, 0)
        vat_amount = to_float(vat.get("amount") if vat else 0, 0)
        discount_amount = to_float(discount.get("amount") if discount else 0, 0)
        expected_total = subtotal + service_charge_amount + vat_amount - discount_amount
        total = to_float(check_data.get("total"), 0)

        if abs(expected_total - total) > 0.01:  # Допускаем погрешность 0.01 из-за float
            error_comments.append(
                f"Total ({total}) does not match calculated total ({expected_total}) "
                f"(subtotal: {subtotal}, service_charge: {service_charge_amount}, "
                f"vat: {vat_amount}, discount: {discount_amount})"
            )

        # Если есть ошибки, записываем их в error_comment
        if error_comments:
            new_check.error_comment = "; ".join(error_comments)
            logger.warning(f"Validation issues for check {check_uuid}: {new_check.error_comment}")

        # Сохраняем изменения в базе данных
        await session.commit()
        logger.debug(f"Check {check_uuid} added to database for user {user_id} as author with items.")
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"Database error in add_check_to_database: {e}")
        raise
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error in add_check_to_database: {e}")
        raise


async def delete_association_by_check_uuid(session: AsyncSession, check_uuid: str, user_id: int):
    try:
        # Удаление записей из user_selections перед удалением ассоциации
        stmt_delete_selections = delete(UserSelection).where(
            UserSelection.user_id == user_id,
            UserSelection.check_uuid == check_uuid
        )
        await session.execute(stmt_delete_selections)

        # Формируем запрос на удаление из user_check_association
        stmt_delete_association = delete(user_check_association).where(
            user_check_association.c.check_uuid == check_uuid,
            user_check_association.c.user_id == user_id
        )
        result = await session.execute(stmt_delete_association)

        # Проверка на наличие ассоциации для удаления
        if result.rowcount == 0:
            logger.warning(f"No association found with check_uuid={check_uuid} and user_id={user_id}.")
            raise ValueError("No association found with the given check_uuid and user_id.")

        # Фиксируем изменения в базе данных
        await session.commit()
        logger.debug(f"Association with check_uuid={check_uuid} and user_id={user_id} deleted successfully.")

    except SQLAlchemyError as e:
        logger.error(
            f"Database error while deleting association for check_uuid={check_uuid} and user_id={user_id}: {e}")
        await session.rollback()
        raise RuntimeError("Database error occurred while deleting the association.")

    except Exception as e:
        logger.error(
            f"Unexpected error while deleting association for check_uuid={check_uuid} and user_id={user_id}: {e}")
        await session.rollback()
        raise RuntimeError("An unexpected error occurred while deleting the association.")


def format_datetime(dt: datetime) -> str:
    """Преобразует datetime в строку ISO формата."""
    return dt.isoformat() if dt else None


async def get_all_checks(session: AsyncSession,
                         user_id: int,
                         page: int,
                         page_size: int,
                         check_name: Optional[str] = None,
                         check_status: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> dict:
    try:
        # Преобразование строковых дат в объекты `date`
        if start_date:
            try:
                start_date = date.fromisoformat(start_date)  # Преобразование строки в дату
            except ValueError:
                raise ValueError(f"Invalid start_date format: {start_date}. Expected format: YYYY-MM-DD")

        if end_date:
            try:
                end_date = date.fromisoformat(end_date)  # Преобразование строки в дату
            except ValueError:
                raise ValueError(f"Invalid end_date format: {end_date}. Expected format: YYYY-MM-DD")

        # Проверка существования пользователя
        user = await session.get(User, user_id)
        if not user:
            logger.warning(f"Пользователь с ID {user_id} не найден.")
            return {
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }

        # Создаём базовый запрос для чеков
        query = select(Check).join(Check.users).where(User.id == user_id)

        # Добавляем фильтры
        if check_name:
            query = query.where(Check.name.ilike(f"%{check_name}%"))
        if check_status:
            query = query.where(Check.status == check_status)
        if start_date:
            query = query.where(Check.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(Check.created_at <= datetime.combine(end_date, datetime.max.time()))

        # Добавляем сортировку по возрастанию даты
        query = query.order_by(Check.created_at.desc())

        # Подсчёт общего количества чеков
        total_checks = await session.scalar(select(func.count()).select_from(query.subquery()))

        # Определяем общее количество страниц и проверяем диапазон страницы
        total_pages = (total_checks + page_size - 1) // page_size
        if page < 1 or page > total_pages:
            logger.warning(
                f"Запрошенная страница {page} выходит за пределы допустимого диапазона для пользователя {user_id}.")
            return {
                "items": [],
                "total": total_checks,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

        # Получаем список чеков с пагинацией
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Выполняем запрос
        result = await session.execute(query)
        checks_page = result.scalars().all()

        return {
            "items": [
                CheckListResponse(
                    uuid=check.uuid,
                    name=check.name,
                    currency=check.check_data.get('currency') if check.check_data else None,
                    status=check.status.value,
                    error_comment=check.error_comment,
                    date=check.created_at.strftime("%d.%m.%Y"),
                    total=to_float(check.total, default=0.0)
                ).model_dump()
                for check in checks_page],
            "total": total_checks,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении чеков для пользователя {user_id}: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": "Ошибка базы данных при получении чеков."
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении чеков для пользователя {user_id}: {e}")
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 0,
            "error": "Произошла неожиданная ошибка."
        }


async def get_main_page_checks(session: AsyncSession, user_id: int) -> dict:
    try:
        # Проверка существования пользователя
        user = await session.get(User, user_id)
        if not user:
            logger.warning(f"Пользователь с ID {user_id} не найден.")
            return {
                "items": [],
                "total_open": 0,
                "total_closed": 0,
            }

        # Подсчёт количества открытых чеков пользователя
        total_open = await session.scalar(
            select(func.count(Check.uuid))
            .join(Check.users)
            .where(and_(User.id == user_id, Check.status == "OPEN"))
        )
        # Подсчёт количества закрытых чеков пользователя
        total_closed = await session.scalar(
            select(func.count(Check.uuid))
            .join(Check.users)
            .where(and_(User.id == user_id, Check.status == "CLOSE"))
        )

        # Получаем список чеков с пагинацией
        result = await session.execute(
            select(Check)
            .join(Check.users)
            .where(User.id == user_id)
            .options(selectinload(Check.users))
            .order_by(Check.created_at.desc())
            .limit(5)
        )
        checks = result.scalars().all()

        return {
            "items": [
                CheckListResponse(
                    uuid=check.uuid,
                    name=check.name,
                    currency=check.check_data.get('currency') if check.check_data else None,
                    status=check.status.value,
                    error_comment=check.error_comment,
                    date=check.created_at.strftime("%d.%m.%Y"),
                    total=to_float(check.total, default=0.0)
                ).model_dump()
                for check in checks
            ],
            "total_open": total_open,
            "total_closed": total_closed,
        }

    except SQLAlchemyError as e:
        logger.error(f"Ошибка базы данных при получении чеков для пользователя {user_id}: {e}")
        return {
            "items": [],
            "total_open": 0,
            "total_closed": 0,
            "error": "Ошибка базы данных при получении чеков."
        }
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении чеков для пользователя {user_id}: {e}")
        return {
            "items": [],
            "total_open": 0,
            "total_closed": 0,
            "error": "Произошла неожиданная ошибка."
        }


async def is_check_author(session: AsyncSession, user_id: int, check_uuid: str) -> bool:
    """
    Проверяет, является ли пользователь автором чека.

    Args:
        session (AsyncSession): Асинхронная сессия SQLAlchemy
        user_id (int): ID пользователя для проверки
        check_uuid (str): UUID чека для проверки

    Returns:
        bool: True если пользователь является автором, False в противном случае
    """
    result = await session.execute(
        select(Check)
        .where(
            and_(
                Check.uuid == check_uuid,
                Check.author_id == user_id
            )
        )
    )
    return result.scalar_one_or_none() is not None
