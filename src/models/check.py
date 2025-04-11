import enum
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import ForeignKey, UniqueConstraint, Enum, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.models.associations import user_check_association


class StatusEnum(enum.Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class Check(Base):
    __tablename__ = "checks"
    uuid: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    check_data: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum), default=StatusEnum.OPEN)
    author_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now
    )
    # Relationships
    author: Mapped["User"] = relationship(
        "User",
        foreign_keys="Check.author_id",
        back_populates="authored_checks"
    )

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


@event.listens_for(Check, 'before_insert')
def generate_name(mapper, connection, target):
    # Генерируем имя по шаблону "check_created_at_первая часть uuid до тире"
    if target.created_at is None:
        target.created_at = datetime.now()
    created_at_str = target.created_at.strftime('%Y%m%d')
    uuid_part = target.uuid.split('-')[0]
    # Получаем имя ресторана из check_data, если оно существует.
    restaurant_name = target.check_data.get('restaurant', '')
    if restaurant_name:  # Если имя ресторана не пустое
        target.name = f"{restaurant_name}_{created_at_str}_{uuid_part}"
    else:
        target.name = f"check_{created_at_str}_{uuid_part}"


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
    check: Mapped[Check] = relationship(back_populates="user_selections")

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'check_uuid',
            name='uq_user_selection_user_check'
        ),
    )

    def __repr__(self) -> str:
        return f"UserSelection(user_id={self.user_id}, check_uuid={self.check_uuid})"
