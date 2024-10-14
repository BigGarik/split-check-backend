from sqlalchemy import select
from sqlalchemy.orm import Session
from app import schemas
from passlib.hash import bcrypt

from app.models import User


# Функция для получения пользователя из БД по email
async def get_user_by_email(db: Session, email: str):
    stmt = select(User).filter_by(email=email)
    result = db.execute(stmt).scalars().first()
    return result


async def create_new_user(db: Session, user: schemas.UserCreate):
    hashed_password = bcrypt.hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
