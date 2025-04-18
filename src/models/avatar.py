# src/models/avatar.py
from sqlalchemy import String, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Avatar(Base):
    __tablename__ = "avatars"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(100))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    content_type: Mapped[str] = mapped_column(String(50))

    def __str__(self) -> str:
        return f"Avatar: {self.filename}"

    def __repr__(self) -> str:
        return f"Avatar(id={self.id}, filename={self.filename})"