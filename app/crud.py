from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app import schemas
from passlib.hash import bcrypt

from app.database import get_async_db
from app.models import User


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


async def create_new_user(user: schemas.UserCreate):
    async with get_async_db() as session:
        hashed_password = bcrypt.hash(user.password)
        db_user = User(email=user.email, hashed_password=hashed_password)
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
        return db_user
