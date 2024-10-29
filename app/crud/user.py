from typing import List, Optional

from fastapi import HTTPException, status
from loguru import logger
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import get_async_db
from app.models import User, user_check_association, Check, UserProfile
from app.schemas import UserCreate, UserProfileUpdate


async def create_new_user(user: UserCreate):
    async with get_async_db() as session:
        hashed_password = bcrypt.hash(user.password)
        db_user = User(email=user.email, hashed_password=hashed_password)
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user


# Функция для получения пользователя из БД по email
async def get_user_by_email(email: str):
    async with get_async_db() as session:
        stmt = select(User).filter_by(email=email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        return user


async def get_user_by_id(user_id: int):
    async with get_async_db() as session:
        stmt = select(User).options(joinedload(User.checks)).filter_by(id=user_id)
        result = await session.execute(stmt)
        user = result.scalars().first()
        return user


async def get_users_by_check(check_uuid: str) -> List[User]:
    async with get_async_db() as session:
        # Создаем запрос для выбора пользователей, связанных с чеком
        query = (
            select(User)
            .join(user_check_association, User.id == user_check_association.c.user_id)
            .join(Check, Check.uuid == user_check_association.c.check_uuid)
            .where(Check.uuid == check_uuid)
        )

        result = await session.execute(query)
        users = result.scalars().all()

        return users


async def join_user_to_check(user_id: int, check_uuid: str):
    """
    Присоединяет пользователя к чеку, проверяя существование чека
    и отсутствие дублирующих связей.

    Args:
        user_id (int): ID пользователя
        check_uuid (str): UUID чека

    Raises:
        HTTPException: если чек не найден или пользователь уже присоединен
    """
    async with get_async_db() as session:
        # Проверяем существование чека
        check_stmt = select(Check).where(Check.uuid == check_uuid)
        check_result = await session.execute(check_stmt)
        check = check_result.scalars().first()

        if not check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check not found"
            )

        # Проверяем существующую связь
        assoc_stmt = (
            select(user_check_association)
            .where(user_check_association.c.user_id == user_id)
            .where(user_check_association.c.check_uuid == check_uuid)
        )
        assoc_result = await session.execute(assoc_stmt)

        if assoc_result.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already joined to this check"
            )

        # Создаем связь
        join_stmt = user_check_association.insert().values(
            user_id=user_id,
            check_uuid=check_uuid
        )
        await session.execute(join_stmt)
        await session.commit()


########################## Профиль пользователя ##########################


async def get_user_profile(user_id: int) -> Optional[UserProfile]:
    async with get_async_db() as session:
        stmt = select(UserProfile).filter_by(user_id=user_id)
        result = await session.execute(stmt)
        return result.scalars().first()


async def create_user_profile(
        user_id: int,
        profile_data: UserProfileUpdate
) -> UserProfile:
    async with get_async_db() as session:
        db_profile = UserProfile(
            user_id=user_id,
            **profile_data.model_dump(exclude_unset=True)
        )
        session.add(db_profile)
        await session.commit()
        await session.refresh(db_profile)
        return db_profile


async def update_user_profile(
        profile: UserProfile,
        profile_data: UserProfileUpdate
) -> UserProfile:
    async with get_async_db() as session:
        update_data = profile_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(profile, field, value)

        await session.commit()
        await session.refresh(profile)
        return profile
