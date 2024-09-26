from sqlalchemy.orm import Session
from app import schemas
from passlib.hash import bcrypt

from app.models import User


# Функция для получения пользователя из БД по email
def get_user_by_email(db: Session, email: str):
    # Предполагаем, что есть функция для поиска пользователя по email
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = bcrypt.hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
