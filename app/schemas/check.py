from typing import List

from pydantic import BaseModel


class ItemSelection(BaseModel):
    item_id: int
    quantity: int


class CheckSelectionRequest(BaseModel):
    selected_items: List[ItemSelection]


class UpdateItemQuantity(BaseModel):
    check_uuid: str
    item_id: int
    quantity: int
