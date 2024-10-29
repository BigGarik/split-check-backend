from sqlalchemy import Table, Column, ForeignKey
from app.database import Base

user_check_association = Table(
    'user_check_association',
    Base.metadata,
    Column('user_id', ForeignKey('users.id', ondelete="CASCADE"), primary_key=True),
    Column('check_uuid', ForeignKey('checks.uuid', ondelete="CASCADE"), primary_key=True)
)