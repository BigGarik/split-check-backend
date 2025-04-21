import base64
from typing import List

from pydantic import BaseModel, ConfigDict


class AvatarResponse(BaseModel):
    id: int
    filename: str
    content_type: str
    data: str  # Base64-encoded data

    model_config = ConfigDict(from_attributes=True)

    # Так как данные хранятся в байтах, а нам нужно их в Base64,
    # создадим модельный метод для этого преобразования
    @classmethod
    def from_orm(cls, obj):
        # Преобразуем байты в Base64-строку
        obj_dict = {
            'id': obj.id,
            'filename': obj.filename,
            'content_type': obj.content_type,
            'data': base64.b64encode(obj.data).decode('utf-8')
        }
        return cls(**obj_dict)


class AvatarListResponse(BaseModel):
    items: List[AvatarResponse]
    total: int