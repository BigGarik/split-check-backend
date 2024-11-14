from typing import List, Optional, Annotated
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError, StringConstraints, conint, confloat, constr

# Кастомные типы с валидацией
PositiveInt = conint(gt=0)
ItemName = constr(min_length=1, max_length=50, strip_whitespace=True)
# Валидация цены до 2 знаков после запятой и диапазона
Price = confloat(gt=0, le=1_000_000_000)


class ItemRequest(BaseModel):
    item_id: PositiveInt = Field(description="ID товара")
    quantity: conint(gt=0, le=1000) = Field(description="Новое количество товара (от 1 до 1000)")


class AddItemRequest(BaseModel):
    uuid: UUID = Field(description="UUID запроса")
    name: ItemName = Field(description="Название товара")
    quantity: PositiveInt = Field(gt=0, le=1000, description="Количество товара (от 1 до 1000)")
    price: Price = Field(description="Цена товара")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }

    # @classmethod
    # def validate_price(cls, price):
    #     """Проверка цены на точность до 2 знаков после запятой"""
    #     if round(price, 2) != price:
    #         raise ValueError("Цена должна иметь не более 2 знаков после запятой")
    #     return price


class EditItemRequest(BaseModel):
    uuid: UUID = Field(description="UUID запроса")
    id: PositiveInt = Field(description="ID товара")
    name: Optional[ItemName] = Field(None, description="Новое название товара")
    quantity: Optional[PositiveInt] = Field(None, description="Новое количество товара (от 1 до 1000)")
    price: Optional[Price] = Field(None, description="Новая цена товара")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }
    #
    # @classmethod
    # def model_post_init(cls, values):
    #     """Проверка, что хотя бы одно поле заполнено"""
    #     if not any(values.get(field) is not None for field in ['name', 'quantity', 'price']):
    #         raise ValueError("Необходимо указать хотя бы одно поле для обновления")
    #     return values


class DeleteItemRequest(BaseModel):
    uuid: UUID = Field(description="UUID запроса")
    id: PositiveInt = Field(description="ID товара")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class CheckSelectionRequest(BaseModel):
    selected_items: Annotated[List[ItemRequest], Field(max_length=100)] = Field(
        default_factory=list,
        description="Список выбранных товаров (до 100 позиций, может быть пустым)"
    )

    # @classmethod
    # def model_post_init(cls, values):
    #     """Валидация уникальности товаров и общего количества"""
    #     item_ids = [item.item_id for item in values['selected_items']]
    #     if len(item_ids) != len(set(item_ids)):
    #         raise ValueError("Найдены дубликаты товаров в списке")
    #
    #     total_quantity = sum(item.quantity for item in values['selected_items'])
    #     if total_quantity > 1000:
    #         raise ValueError("Общее количество товаров не может превышать 1000")
    #     return values


class UpdateItemQuantity(BaseModel):
    check_uuid: UUID = Field(description="UUID чека")
    item_id: PositiveInt = Field(description="ID товара")
    quantity: PositiveInt = Field(gt=0, le=1000, description="Новое количество товара (от 1 до 1000)")

    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


# Пример использования:
if __name__ == "__main__":
    try:
        item = AddItemRequest(
            uuid="123e4567-e89b-12d3-a456-426614174000",
            name="Товар 1",
            quantity=5,
            price=99.99
        )
        print("Валидация успешна:", item.dict())
    except ValidationError as e:
        print("Ошибка валидации:", e)

    try:
        item = AddItemRequest(
            uuid="invalid-uuid",
            name="",
            quantity=-1,
            price=99.999
        )
    except ValidationError as e:
        print("Ожидаемая ошибка валидации:", e)
