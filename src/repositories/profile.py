from typing import Optional

from fastapi import HTTPException
from sqlalchemy.future import select
from loguru import logger
from src.models.profile import UserProfile
from src.schemas import UserProfileUpdate
from src.utils.db import with_db_session


@with_db_session()
async def get_user_profile_db(session, user_id: int) -> Optional[UserProfile]:
    """Получение профиля пользователя по user_id."""
    logger.debug(f'Получение профиля пользователя по user_id: {user_id}')
    stmt = select(UserProfile).filter_by(user_id=user_id)
    result = await session.execute(stmt)
    return result.scalars().first()


@with_db_session()
async def create_user_profile_db(session, user_id: int, profile_data: UserProfileUpdate) -> UserProfile:
    """Создание профиля пользователя."""
    db_profile = UserProfile(
        user_id=user_id,
        **profile_data.model_dump(exclude_unset=True)
    )
    session.add(db_profile)
    await session.commit()
    await session.refresh(db_profile)
    return db_profile


@with_db_session()
async def update_user_profile_db(session, user_id: int, profile_data: UserProfileUpdate) -> UserProfile:
    """Обновление профиля пользователя."""
    profile = await session.get(UserProfile, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await session.commit()
    await session.refresh(profile)
    return profile
