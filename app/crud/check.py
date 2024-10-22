from loguru import logger
from sqlalchemy import select, insert

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
            check_data = check.check_data
            logger.info(f"check_data из базы данных: {check_data}")

    return check_data
