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

        # Создаем нового пользователя
        new_user = User(email=user.email, hashed_password=hashed_password)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)

        # Создаем пустой профиль для нового пользователя
        db_user_profile = UserProfile(user_id=new_user.id)
        session.add(db_user_profile)

        # Сохраняем профиль
        await session.commit()
        await session.refresh(db_user_profile)

        return new_user


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


async def get_users_by_check_uuid(check_uuid: str) -> List[User]:
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


async def join_user_to_check(user_id: int, check_uuid: str) -> dict:
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
        # Проверка на существование чека
        check_stmt = select(Check).where(Check.uuid == check_uuid)
        check_result = await session.execute(check_stmt)
        check = check_result.scalars().first()

        if not check:
            logger.error(f"Чек с UUID {check_uuid} не найден.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Чек не найден"
            )

        # Проверка на существующую связь
        assoc_stmt = (
            select(user_check_association)
            .where(user_check_association.c.user_id == user_id)
            .where(user_check_association.c.check_uuid == check_uuid)
        )
        assoc_result = await session.execute(assoc_stmt)

        if assoc_result.first():
            logger.warning(f"Пользователь {user_id} уже присоединен к чеку {check_uuid}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь уже присоединен к этому чеку"
            )

        # Создание связи
        try:
            join_stmt = user_check_association.insert().values(
                user_id=user_id,
                check_uuid=check_uuid
            )
            await session.execute(join_stmt)
            await session.commit()
            logger.info(f"Пользователь {user_id} успешно присоединен к чеку {check_uuid}.")
        except Exception as e:
            logger.error(f"Ошибка при присоединении пользователя {user_id} к чеку {check_uuid}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось присоединить пользователя к чеку"
            )

        result = {
            "status": "success",
            "message": "Пользователь успешно присоединен к чеку"
        }

        return result


########################## Профиль пользователя ##########################


async def get_user_profile_db(user_id: int) -> Optional[UserProfile]:
    async with get_async_db() as session:
        stmt = select(UserProfile).filter_by(user_id=user_id)
        result = await session.execute(stmt)
        return result.scalars().first()


async def create_user_profile_db(
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


async def update_user_profile_db(
        user_id: int,
        profile_data: UserProfileUpdate
) -> UserProfile:
    async with get_async_db() as session:
        # Получаем профиль пользователя по user_id
        profile = await session.get(UserProfile, user_id)
        logger.debug(f"Profile: {profile}")

        # Проверка, существует ли профиль
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Обновление полей профиля только с данными, которые были переданы
        update_data = profile_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            # Изменяем только те поля, которые переданы и не None
            if value is not None:
                setattr(profile, field, value)

        # Сохраняем изменения в базе данных
        await session.commit()
        await session.refresh(profile)

        return profile
