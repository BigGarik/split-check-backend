from datetime import datetime
from typing import List

from sqlalchemy import Column, Integer, String, Table, ForeignKey, JSON, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Промежуточная таблица для связи "многие ко многим"
user_check_association = Table(
    'user_check_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('check_uuid', String, ForeignKey('checks.uuid', ondelete='CASCADE'), primary_key=True)
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связь через промежуточную таблицу
    checks: Mapped[list["Check"]] = relationship("Check", secondary=user_check_association, back_populates="users")
    user_selections: Mapped[List["UserSelection"]] = relationship("UserSelection", back_populates="user", cascade="all, delete")

    def __str__(self):
        return f"User: {self.email}"


class Check(Base):
    __tablename__ = "checks"

    uuid: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    check_data: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Связь через промежуточную таблицу
    users: Mapped[list[User]] = relationship("User", secondary=user_check_association, back_populates="checks")
    user_selections: Mapped[List["UserSelection"]] = relationship("UserSelection", back_populates="check", cascade="all, delete")


class UserSelection(Base):
    __tablename__ = "user_selections"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    check_uuid: Mapped[str] = mapped_column(String, ForeignKey("checks.uuid", ondelete="CASCADE"), primary_key=True)
    selection: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    user: Mapped[User] = relationship("User", back_populates="user_selections", cascade="all, delete")
    check: Mapped[Check] = relationship("Check", back_populates="user_selections", cascade="all, delete")

    __table_args__ = (
        UniqueConstraint('user_id', 'check_uuid', name='uq_user_check'),  # Ограничение уникальности
    )

