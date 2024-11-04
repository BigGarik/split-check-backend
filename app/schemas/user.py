from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    id: int
    email: str
    model_config = ConfigDict(from_attributes=True)


class UserProfileBase(BaseModel):
    nickname: Optional[str] = Field(None, max_length=50)
    language: Optional[str] = Field(None, max_length=10)
    avatar_url: Optional[str] = Field(None, max_length=255)


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
