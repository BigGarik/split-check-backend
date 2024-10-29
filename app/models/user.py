from datetime import datetime
from typing import List, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from .association import user_check_association


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    hashed_password: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now
    )
    # Связи
    profile: Mapped["UserProfile"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    checks: Mapped[List["Check"]] = relationship(
        secondary=user_check_association,
        back_populates="users",
        cascade="all, delete"
    )
    user_selections: Mapped[List["UserSelection"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"User: {self.email}"

    def __repr__(self) -> str:
        return f"User(id={self.id}, email={self.email})"


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    nickname: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now
    )
    # Связь с пользователем
    user: Mapped[User] = relationship(back_populates="profile")

    def __str__(self) -> str:
        return f"UserProfile: {self.nickname or 'No nickname'}"

    def __repr__(self) -> str:
        return f"UserProfile(id={self.id}, user_id={self.user_id}, nickname={self.nickname})"