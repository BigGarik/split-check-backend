from typing import List, Optional
from pydantic import BaseModel, Field, model_validator, conint, confloat, constr, field_validator

# Кастомные типы с валидацией
PositiveInt = conint(gt=0)
ItemName = constr(min_length=1, max_length=50, strip_whitespace=True)
# Валидация цены до 2 знаков после запятой и диапазона
Price = confloat(gt=0, le=1_000_000_000)


class ItemRequest(BaseModel):
    item_id: PositiveInt = Field(description="ID товара")
    quantity: conint(gt=0, le=1000) = Field(description="Новое количество товара (от 1 до 1000)")


class AddItemRequest(BaseModel):
    name: ItemName = Field(description="Название товара")
    quantity: PositiveInt = Field(gt=0, le=1000, description="Количество товара (от 1 до 1000)")
    price: Price = Field(description="Цена товара")

    # Валидация цены до 2 знаков после запятой
    @field_validator('price')
    def validate_price(cls, value: float) -> float:
        if round(value, 2) != value:
            raise ValueError("Цена должна иметь не более 2 знаков после запятой")
        return value


class EditItemRequest(BaseModel):
    id: PositiveInt = Field(description="ID товара")
    name: Optional[ItemName] = Field(None, description="Новое название товара")
    quantity: Optional[PositiveInt] = Field(None, gt=0, le=1000, description="Новое количество товара (от 1 до 1000)")
    price: Optional[Price] = Field(None, description="Новая цена товара")

    # Проверка, что хотя бы одно поле заполнено
    @model_validator(mode='after')
    def check_at_least_one_field(cls, model):
        # Проверяем, что хотя бы одно из полей (кроме id) заполнено
        if not any(getattr(model, field) is not None for field in ['name', 'quantity', 'price']):
            raise ValueError("Необходимо указать хотя бы одно поле для обновления")
        return model


class DeleteItemRequest(BaseModel):
    id: PositiveInt = Field(description="ID товара")


class CheckSelectionRequest(BaseModel):
    selected_items: List[ItemRequest] = Field(default_factory=list, description="Список выбранных товаров")


class CheckListResponse(BaseModel):
    uuid: str
    name: str
    status: str
    date: str
    total: Optional[Price]
    restaurant: str
