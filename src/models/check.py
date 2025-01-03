from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.models.associations import user_check_association


class Check(Base):
    __tablename__ = "checks"
    uuid: Mapped[str] = mapped_column(primary_key=True)
    check_data: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    is_open: Mapped[bool] = mapped_column(default=True)
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
