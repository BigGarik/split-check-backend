# src/repositories/image.py
import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.avatar import Avatar
from src.utils.db import with_db_session

logger = logging.getLogger(__name__)


@with_db_session()
async def create_avatar(session: AsyncSession, filename: str, content_type: str, data: bytes) -> Avatar:
    """
    Создание нового изображения-аватара или обновление существующего.
    Если аватар с таким именем файла уже существует, он будет обновлен.
    """
    # Сначала проверяем, существует ли аватар с таким именем файла
    stmt = select(Avatar).where(Avatar.filename == filename)
    result = await session.execute(stmt)
    existing_avatar = result.scalar_one_or_none()

    if existing_avatar:
        # Если аватар существует, обновляем его данные
        existing_avatar.content_type = content_type
        existing_avatar.data = data
        await session.commit()
        await session.refresh(existing_avatar)
        return existing_avatar
    else:
        # Создаем новый аватар
        avatar = Avatar(
            filename=filename,
            content_type=content_type,
            data=data
        )
        session.add(avatar)
        await session.commit()
        await session.refresh(avatar)
        return avatar


@with_db_session()
async def get_all_avatars(session: AsyncSession) -> List[Avatar]:
    """Получение всех изображений."""
    stmt = select(Avatar).order_by(Avatar.id.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@with_db_session()
async def get_avatar_by_id(session: AsyncSession, avatar_id: int) -> Optional[Avatar]:
    """Получение изображения по ID."""
    stmt = select(Avatar).filter_by(id=avatar_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()