from sqlalchemy.orm import DeclarativeBase
from .session import metadata


class Base(DeclarativeBase):
    metadata = metadata
