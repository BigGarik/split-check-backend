from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str
    model_config = ConfigDict(from_attributes=True)


class User(BaseModel):
    id: int
    email: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserProfileBase(BaseModel):
    nickname: Optional[str] = None
    language: Optional[str] = None
    avatar_url: Optional[str] = None


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
