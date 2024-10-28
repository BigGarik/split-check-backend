from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import Column, Table, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Промежуточная таблица для связи "многие ко многим"
user_check_association = Table(
    'user_check_association',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('check_uuid', ForeignKey('checks.uuid', ondelete="CASCADE"), primary_key=True)
)


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


class Check(Base):
    __tablename__ = "checks"

    uuid: Mapped[str] = mapped_column(primary_key=True)
    check_data: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        secondary=user_check_association,
        back_populates="checks",
        cascade="all, delete"
    )
    user_selections: Mapped[List["UserSelection"]] = relationship(
        back_populates="check",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Check(uuid={self.uuid})"


class UserSelection(Base):
    __tablename__ = "user_selections"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    check_uuid: Mapped[str] = mapped_column(
        ForeignKey("checks.uuid", ondelete="CASCADE"),
        primary_key=True
    )
    selection: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="user_selections")
    check: Mapped["Check"] = relationship(back_populates="user_selections")

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'check_uuid',
            name='uq_user_selection_user_check'
        ),
    )

    def __repr__(self) -> str:
        return f"UserSelection(user_id={self.user_id}, check_uuid={self.check_uuid})"
