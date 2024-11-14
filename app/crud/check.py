import json
from datetime import datetime

from loguru import logger
from sqlalchemy import select, insert, delete, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.database import with_db_session
from app.models import Check, user_check_association, User
from app.redis import redis_client
from config import settings


@with_db_session()
async def add_check_to_database(session: AsyncSession, check_uuid: str, user_id: int, recognized_json: dict):
    try:
        # Создаем новый чек
        new_check = Check(uuid=check_uuid, check_data=recognized_json)
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


@with_db_session()
async def get_check_data_by_uuid(session: AsyncSession, check_uuid: str):
    redis_key = f"check_uuid:{check_uuid}"

    try:
        # Пытаемся получить данные чека из Redis
        check_data = await redis_client.get(redis_key)
        if check_data:
            # Преобразуем данные из строки (JSON) в словарь (dict)
            check_data = json.loads(check_data)
            logger.debug(f"Данные чека найдены в Redis: {check_data}")
            return check_data

        # Если данных нет в Redis, ищем в базе данных
        stmt = select(Check).filter_by(uuid=check_uuid)
        result = await session.execute(stmt)
        check = result.scalars().first()

        if check:
            # Конвертируем данные чека из базы данных в JSON
            check_data = check.check_data
            logger.debug(f"Данные чека найдены в базе данных для UUID: {check_uuid}")

            # Кэшируем данные чека в Redis для будущих обращений
            await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
            return check_data

        # Логирование случая, если чек не найден
        logger.warning(f"Чек с UUID {check_uuid} не найден в базе данных.")
        return None

    except SQLAlchemyError as e:
        # Обработка ошибок SQLAlchemy
        logger.error(f"Ошибка при доступе к базе данных: {e}")
        return None

    except Exception as e:
        # Обработка других возможных ошибок
        logger.error(f"Неожиданная ошибка при получении данных чека: {e}")
        return None



@with_db_session()
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
                updated = True
                logger.info(f"Обновлено количество для элемента {item_id} в чеке {check_uuid} на {quantity}")
                break

        if not updated:
            logger.warning(f"Элемент с ID {item_id} не найден в чеке {check_uuid}")
            raise ValueError("Item not found in check data")

        # Явное обновление поля check_data
        flag_modified(check, "check_data")
        await session.commit()

        # Обновление кэша Redis, если данные изменены
        redis_key = f"check_uuid:{check_uuid}"
        await redis_client.set(redis_key, json.dumps(check.check_data), expire=settings.redis_expiration)
        logger.info(f"Данные чека {check_uuid} обновлены в Redis.")

    except SQLAlchemyError as e:
        logger.error(f"Ошибка при обновлении чека в базе данных: {e}")
        await session.rollback()
        raise

    except Exception as e:
        logger.error(f"Неожиданная ошибка при обновлении количества элемента: {e}")
        raise


@with_db_session()
async def delete_association_by_check_uuid(session: AsyncSession, check_uuid: str, user_id: int):
    try:
        # Формируем запрос на удаление
        stmt = delete(user_check_association).where(
            user_check_association.c.check_uuid == check_uuid,
            user_check_association.c.user_id == user_id
        )

        # Выполняем запрос
        result = await session.execute(stmt)

        # Проверка на наличие ассоциации для удаления
        if result.rowcount == 0:
            logger.warning(f"No association found with check_uuid={check_uuid} and user_id={user_id}.")
            raise ValueError("No association found with the given check_uuid and user_id.")

        # Фиксируем изменения в базе данных
        await session.commit()
        logger.debug(f"Association with check_uuid={check_uuid} and user_id={user_id} deleted successfully.")

    except SQLAlchemyError as e:
        logger.error(f"Database error while deleting association for check_uuid={check_uuid} and user_id={user_id}: {e}")
        await session.rollback()
        raise RuntimeError("Database error occurred while deleting the association.")

    except Exception as e:
        logger.error(f"Unexpected error while deleting association for check_uuid={check_uuid} and user_id={user_id}: {e}")
        await session.rollback()
        raise RuntimeError("An unexpected error occurred while deleting the association.")


@with_db_session()
async def get_all_checks(session: AsyncSession, user_id: int, page: int = 1, page_size: int = 10) -> dict:
    def format_datetime(dt: datetime) -> str:
        """Преобразует datetime в строку ISO формата."""
        return dt.isoformat() if dt else None
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
            logger.warning(f"Запрошенная страница {page} выходит за пределы допустимого диапазона для пользователя {user_id}.")
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
