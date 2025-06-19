from pydantic import BaseModel


class LogLevelUpdateRequest(BaseModel):
    level: str = "INFO"