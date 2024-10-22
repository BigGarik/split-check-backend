from typing import List

from loguru import logger
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.database import get_async_db
from app.models import User, user_check_association, Check
from app.schemas import UserCreate


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
