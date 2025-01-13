from datetime import date, time, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, computed_field
from pydantic import model_validator, conint, confloat, constr

# Кастомные типы с валидацией
PositiveInt = conint(gt=0)
ItemName = constr(min_length=1, max_length=50, strip_whitespace=True)
# Валидация цены до 2 знаков после запятой и диапазона
Price = confloat(ge=0, le=1_000_000_000)


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
    restaurant: Optional[str] = None


# Валидатор для позиции в чеке
class Item(BaseModel):
    id: int
    name: str
    quantity: Decimal = Field(gt=0)  # Позволяем дробные значения
    price: Decimal = Field(gt=0)


# Валидатор для сервисного сбора
class ServiceCharge(BaseModel):
    name: str
    amount: Decimal = Field(ge=0)


# Валидатор для НДС
class VAT(BaseModel):
    rate: Decimal = Field(ge=0)
    amount: Decimal = Field(ge=0)

    @classmethod
    @field_validator("amount")
    def validate_vat_amount(cls, v: Decimal, info) -> Decimal:
        """Проверка: если ставка НДС равна 0, то и сумма НДС должна быть равна 0."""
        rate = info.data.get("rate", 0)
        if rate == 0 and v != 0:
            raise ValueError("VAT amount должен быть 0, если rate равен 0")
        return v


# Валидатор для общего заказа
class Order(BaseModel):
    restaurant: Optional[str] = None
    table_number: Optional[str] = None
    order_number: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    waiter: Optional[str] = None
    items: List[Item]
    subtotal: Decimal
    service_charge: Optional[ServiceCharge] = None
    vat: Optional[VAT] = None
    total: Decimal

    @classmethod
    @field_validator('date', mode='before')
    def parse_date(cls, v: Optional[str]) -> Optional[date]:
        if v is None:
            return None
        if isinstance(v, str):
            day, month, year = map(int, v.split('.'))
            return date(year, month, day)
        return v

    @classmethod
    @field_validator('time', mode='before')
    def parse_time(cls, v: Optional[str]) -> Optional[time]:
        if v is None:
            return None
        if isinstance(v, str):
            hour, minute = map(int, v.split(':'))
            return time(hour, minute)
        return v

    @classmethod
    @field_validator('subtotal')
    def validate_subtotal(cls, v: Decimal, info) -> Decimal:
        items = info.data.get('items', [])
        calculated_subtotal = sum(item.total for item in items)
        if v != calculated_subtotal:
            raise ValueError(
                f'Неверный subtotal. Ожидается {calculated_subtotal}, получено {v}'
            )
        return v

    @classmethod
    @field_validator('total')
    def validate_total(cls, v: Decimal, info) -> Decimal:
        subtotal = info.data.get('subtotal', 0)
        service_charge = info.data.get('service_charge')
        vat = info.data.get('vat')

        calculated_total = subtotal + (service_charge.amount if service_charge else 0) + (vat.amount if vat else 0)
        if v != calculated_total:
            raise ValueError(
                f'Неверный total. Ожидается {calculated_total}, получено {v}'
            )
        return v
