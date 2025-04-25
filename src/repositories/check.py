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
from src.repositories.user_selection import get_user_selection_by_check_uuid
from src.schemas import CheckListResponse
from src.utils.db import with_db_session

logger = logging.getLogger(__name__)


async def get_check_by_uuid(session: AsyncSession, check_uuid: str) -> Optional[Check]:
    stmt = select(Check).filter_by(uuid=check_uuid)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


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


async def update_check_data_to_database(session: AsyncSession, check_uuid: str, check_data: dict):
    check = await get_check_by_uuid(session, check_uuid)
    if not check:
        raise HTTPException(status_code=404, detail="Check not found")

    # Обновляем данные чека
    check.check_data = check_data
    flag_modified(check, "check_data")
    await session.commit()


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
    Создает новый чек в базе данных и устанавливает связь с пользователем.

    Функция выполняет следующие операции:
    1. Создает новую запись в таблице checks
    2. Устанавливает пользователя как автора чека
    3. Создает связь между пользователем и чеком в таблице ассоциаций

    Args:
        session (AsyncSession): Асинхронная сессия SQLAlchemy для работы с БД
        check_uuid (str): Уникальный идентификатор создаваемого чека
        user_id (int): ID пользователя, который создает чек
        check_data (dict): Данные чека для сохранения в формате JSON

    Raises:
        SQLAlchemyError: При ошибках работы с базой данных
        Exception: При любых других непредвиденных ошибках
    """
    try:
        # Создаем новый чек с указанием автора
        new_check = Check(
            uuid=check_uuid,
            check_data=check_data,
            author_id=user_id
        )
        session.add(new_check)
        await session.flush()

        # Создаем связь между пользователем и чеком
        stmt = insert(user_check_association).values(
            user_id=user_id,
            check_uuid=check_uuid
        )
        await session.execute(stmt)

        # Сохраняем изменения в базе данных
        await session.commit()
        logger.debug(f"Check {check_uuid} added to database for user {user_id} as author.")
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
                    currency=check.currency,
                    status=check.status.value,
                    date=check.created_at.strftime("%d.%m.%Y"),
                    total=check.check_data.get('total') if check.check_data else None,
                    restaurant=check.check_data.get('restaurant') if check.check_data else None,
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
                    date=check.created_at.strftime("%d.%m.%Y"),
                    total=check.check_data.get('total') if check.check_data else 0,
                    restaurant=check.check_data.get('restaurant') if check.check_data else None,
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


async def is_user_check_association(session: AsyncSession, user_id: int, check_uuid: str) -> bool:
    result = await session.execute(
        select(user_check_association).where(
            and_(
                user_check_association.c.user_id == user_id,
                user_check_association.c.check_uuid == check_uuid
            )
        )
    )
    exists = result.scalar_one_or_none() is not None
    logger.debug(f"Проверка наличия ассоциации для пользователя {user_id} и чека {check_uuid}: {exists}")
    return exists


async def get_check_data_by_uuid(session: AsyncSession, check_uuid: str) -> Dict[str, Any]:
    redis_key = f"check_uuid:{check_uuid}"

    # Попытка получить данные из Redis
    cached_data = await redis_client.get(redis_key)
    if cached_data:
        logger.debug(f"Получены данные чека из Redis: {cached_data}")
        return json.loads(cached_data)

    # Если нет в Redis, ищем в базе данных
    check = await get_check_by_uuid(session, check_uuid)
    if not check:
        logger.warning(f"Чек не найден: {check_uuid}")
        raise HTTPException(status_code=404, detail="Check not found")

    # Кэширование в Redis
    await redis_client.set(
        redis_key,
        json.dumps(check.check_data),
        expire=REDIS_EXPIRATION
    )

    logger.debug(f"Данные чека получены из БД: {check.check_data}")
    return check.check_data


async def get_check_data(session: AsyncSession, user_id: int, check_uuid: str) -> dict:
    try:
        is_check_association = await is_user_check_association(session, user_id, check_uuid)
        logger.debug(f"is_check_association: {is_check_association}")
        if not is_check_association:
            raise HTTPException(status_code=404, detail="Check not found")

        check_data = await get_check_data_by_uuid(session, check_uuid)

        logger.debug(f"check_data: {check_data}")

        participants, user_selections, _ = await get_user_selection_by_check_uuid(session, check_uuid)

        check_data["participants"] = json.loads(participants)
        check_data["user_selections"] = json.loads(user_selections)
        check = await get_check_by_uuid(session, check_uuid)
        check_data["name"] = check.name
        check_data["date"] = check.created_at.strftime("%d.%m.%Y")
        check_data["uuid"] = check_uuid
        check_data["author_id"] = check.author_id
        check_data["status"] = check.status.value

        return check_data

    except Exception as e:
        logger.error(f"Ошибка при получении данных чека: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")