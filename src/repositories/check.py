from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import select, insert, delete, func, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from starlette.exceptions import HTTPException

from src.models import Check, user_check_association, User, UserSelection


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


async def add_check_to_database(session: AsyncSession, check_uuid: str, user_id: int, check_data: dict):
    try:
        # Создаем новый чек
        new_check = Check(uuid=check_uuid, check_data=check_data)
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
        logger.debug(f"Check {check_uuid} added to database for user {user_id}.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Unexpected error in add_check_to_database: {e}")
        raise e


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


async def get_all_checks(session: AsyncSession, user_id: int, page: int = 1, page_size: int = 10) -> dict:
    try:
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

        # Подсчёт общего количества чеков пользователя
        total_checks = await session.scalar(
            select(func.count(Check.uuid))
            .join(Check.users)
            .where(User.id == user_id)
        )

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
        checks = await session.execute(
            select(Check)
            .join(Check.users)
            .where(User.id == user_id)
            .options(selectinload(Check.users))
            .order_by(Check.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        checks_page = checks.scalars().all()

        return {
            "items": [{
                "uuid": check.uuid,
                "created_at": format_datetime(check.created_at)
            } for check in checks_page],
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
            "items": [{
                "uuid": check.uuid,
                "status": check.status.value,
                "date": check.check_data.get('date') if check.check_data else None,
                "total": check.check_data.get('total') if check.check_data else None,
                "restaurant": check.check_data.get('restaurant') if check.check_data else None,
            } for check in checks],
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
