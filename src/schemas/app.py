from typing import Literal

from pydantic import BaseModel


class LogLevelUpdateRequest(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"