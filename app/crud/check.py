import json

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select, insert, delete
from sqlalchemy.orm.attributes import flag_modified

from app.database import get_async_db
from app.models import Check, user_check_association
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
            raise HTTPException(status_code=404, detail="Check not found")

        # Обновление количества, если элемент найден
        updated = False
        for item in check.check_data.get("items", []):
            if item["id"] == item_id:
                item["quantity"] = quantity
                updated = True
                break

        if not updated:
            raise HTTPException(status_code=404, detail="Item not found in check data")

        # Явное обновление данных и сохранение
        flag_modified(check, "check_data")
        await session.commit()


async def delete_association_by_check_uuid(check_uuid: str, user_id: int):
    async with get_async_db() as session:
        try:
            # Создаем запрос на удаление
            stmt = delete(user_check_association).where(user_check_association.c.check_uuid == check_uuid,
                                                        user_check_association.c.user_id == user_id)

            # Выполняем запрос
            result = await session.execute(stmt)

            # Фиксируем изменения в базе данных
            await session.commit()

            if result.rowcount == 0:
                raise HTTPException(status_code=404, detail="No association found with the given check_uuid")

            logger.info(f"Association with check_uuid={check_uuid} has been deleted successfully.")
            # Возвращаем результат
            return True

        except Exception as e:
            logger.error(f"Error deleting association: {e}")
            await session.rollback()
            raise HTTPException(status_code=500, detail="An error occurred while deleting the association")
