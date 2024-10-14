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


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: str | None = None


class Task(BaseModel):
    type: str
    data: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str
