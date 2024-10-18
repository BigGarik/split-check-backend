from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from passlib.hash import bcrypt

from app.database import get_async_db
from app.models import User


# Функция для получения пользователя из БД по email
async def get_user_by_email(session: AsyncSession, email: str):
    stmt = select(User).filter_by(email=email)
    result = await session.execute(stmt)
    user = result.scalars().first()
    return user


async def get_user_by_id(user_id: int, session: AsyncSession = Depends(get_async_db)):
    stmt = select(User).filter_by(id=user_id)
    result = await session.execute(stmt)
    user = result.scalars().first()
    return user


async def create_new_user(session: AsyncSession, user: schemas.UserCreate):
    hashed_password = bcrypt.hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user
