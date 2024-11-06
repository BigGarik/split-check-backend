from typing import List, Optional

from pydantic import BaseModel, Field


class ItemSelection(BaseModel):
    item_id: int
    quantity: int


class AddItemRequest(BaseModel):
    uuid: str
    name: str
    quantity: int
    price: float


class EditItemRequest(BaseModel):
    uuid: str
    id: int
    name: Optional[str] = Field(None, max_length=50)
    quantity: Optional[int] = Field(None)
    price: Optional[float] = Field(None)


class DeliteItemRequest(BaseModel):
    uuid: str
    id: int


class CheckSelectionRequest(BaseModel):
    selected_items: List[ItemSelection]


class UpdateItemQuantity(BaseModel):
    check_uuid: str
    item_id: int
    quantity: int
