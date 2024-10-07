from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str

    class Config:
        from_attributes = True


class User(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True


# Схема для токена
class TokenData(BaseModel):
    email: str | None = None


# Модель для возвращения статуса задачи
class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: str = None
