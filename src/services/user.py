import logging

from fastapi import HTTPException, status
from sqlalchemy.future import select

from src.config import config
from src.models.check import Check, user_check_association
from src.utils.db import with_db_session

logger = logging.getLogger(config.app.service_name)


@with_db_session()
async def join_user_to_check(session, user_id: int, check_uuid: str) -> dict:
    """Присоединяет пользователя к чеку, проверяя существование чека и отсутствие дублирующих связей."""
    check_stmt = select(Check).where(Check.uuid == check_uuid)
    check_result = await session.execute(check_stmt)
    check = check_result.scalars().first()

    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чек не найден")

    assoc_stmt = (
        select(user_check_association)
        .where(user_check_association.c.user_id == user_id)
        .where(user_check_association.c.check_uuid == check_uuid)
    )
    assoc_result = await session.execute(assoc_stmt)

    if assoc_result.first():
        return {"status": "success", "message": "Пользователь успешно присоединен"}

    try:
        join_stmt = user_check_association.insert().values(
            user_id=user_id,
            check_uuid=check_uuid
        )
        await session.execute(join_stmt)
        await session.commit()
        return {"status": "success", "message": "Пользователь успешно присоединен"}
    except Exception as e:
        logger.error(f"Ошибка при присоединении пользователя: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка добавления")
