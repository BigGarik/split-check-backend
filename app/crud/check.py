import json

from loguru import logger
from sqlalchemy import select, insert, delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_async_db
from app.models import Check, user_check_association, User
from app.redis import redis_client


async def add_check_to_database(check_uuid: str, user_id: int, recognized_json: dict):
    async with get_async_db() as session:
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


async def get_check_data_by_uuid(check_uuid: str):
    # Ищем данные чека в Redis по uuid
    redis_key = f"check_uuid:{check_uuid}"
    check_data = await redis_client.get(redis_key)
    logger.info(f"check_data из Redis: {check_data}")
    if not check_data:
        async with get_async_db() as session:
            stmt = select(Check).filter_by(uuid=check_uuid)
            result = await session.execute(stmt)
            check = result.scalars().first()
            check_data = json.dumps(check.check_data)
            logger.info(f"check_data из базы данных: {check_data}")

    return check_data


async def update_item_quantity(check_uuid: str, item_id: int, quantity: int):
    async with get_async_db() as session:
        # Проверка существования чека
        check = await session.get(Check, check_uuid)
        if not check:
            raise Exception("Check not found")

        # Обновление количества, если элемент найден
        updated = False
        for item in check.check_data.get("items", []):
            if item["id"] == item_id:
                item["quantity"] = quantity
                updated = True
                break

        if not updated:
            raise Exception("Item not found in check data")

        # Явное обновление данных и сохранение
        flag_modified(check, "check_data")
        await session.commit()


async def delete_association_by_check_uuid(check_uuid: str, user_id: int):
    async with get_async_db() as session:
        try:
            # Создаем запрос на удаление
            stmt = delete(user_check_association).where(
                user_check_association.c.check_uuid == check_uuid,
                user_check_association.c.user_id == user_id)

            # Выполняем запрос
            result = await session.execute(stmt)

            # Фиксируем изменения в базе данных
            await session.commit()

            if result.rowcount == 0:
                raise Exception("No association found with the given check_uuid")

            logger.info(f"Association with check_uuid={check_uuid} has been deleted successfully.")

        except Exception as e:
            logger.error(f"Error deleting association: {e}")
            await session.rollback()
            raise Exception("An error occurred while deleting the association")


async def get_all_checks(user_id: int, page: int = 1, page_size: int = 10) -> dict:
    async with get_async_db() as session:
        try:
            # Проверка, существует ли пользователь с данным user_id
            user_exists = await session.get(User, user_id)
            if not user_exists:
                logger.warning(f"Пользователь с ID {user_id} не найден.")
                return {
                    "items": [],
                    "total": 0,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": 0
                }

            # Подсчет общего количества чеков пользователя
            total_checks = await session.scalar(
                select(func.count(Check.uuid))
                .where(Check.users.any(User.id == user_id))  # Используем связь many-to-many
            )

            # Определяем общее количество страниц
            total_pages = (total_checks + page_size - 1) // page_size

            # Если указана страница за пределами допустимого диапазона, возвращаем пустой результат
            if page > total_pages:
                return {
                    "items": [],
                    "total": total_checks,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }

            # Получаем список чеков с пагинацией
            checks = await session.execute(
                select(Check)
                .where(Check.users.any(User.id == user_id))
                .options(selectinload(Check.users))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            checks_page = checks.scalars().all()

            return {
                "items": [check.uuid for check in checks_page],
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
