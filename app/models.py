from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Промежуточная таблица для связи "многие ко многим"
user_check_association = Table(
    'user_check_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('check_uuid', String, ForeignKey('checks.uuid'), primary_key=True)
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    # Связь через промежуточную таблицу
    checks: Mapped[list["Check"]] = relationship("Check", secondary=user_check_association, back_populates="users")


class Check(Base):
    __tablename__ = "checks"

    uuid: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Связь через промежуточную таблицу
    users: Mapped[list[User]] = relationship("User", secondary=user_check_association, back_populates="checks")

