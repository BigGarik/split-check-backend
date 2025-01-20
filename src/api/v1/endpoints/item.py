from uuid import UUID

from fastapi import APIRouter, Depends, Request
from loguru import logger

from src.api.deps import get_current_user
from src.models import User
from src.redis import queue_processor
from src.schemas import ItemRequest, AddItemRequest, EditItemRequest

router = APIRouter()


@router.put("/item/split")
async def split_item(request: Request,
                     uuid: UUID,
                     item_data: ItemRequest,
                     user: User = Depends(get_current_user)):
    """Разделяет позицию на части и отправляет задачу в очередь Redis."""
    # Формируем данные задачи
    task_data = {
        "type": "split_item_task",
        "check_uuid": str(uuid),
        "user_id": user.id,
        "item_data": item_data.model_dump()
    }
    logger.debug(f"Позиция отправлена для разделения: {item_data}")

    # Добавляем задачу в очередь Redis
    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в очередь для обработки"}


@router.post("/item/add")
async def add_item(request: Request,
                   uuid: UUID,
                   item_data: AddItemRequest,
                   user: User = Depends(get_current_user)):
    """Добавляет позицию в чек."""
    task_data = {
        "type": "add_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_data": item_data.model_dump()
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}


@router.post("/item/edit")
async def add_item(request: Request,
                   uuid: UUID,
                   item_data: EditItemRequest,
                   user: User = Depends(get_current_user)):
    """Редактирование позиции в чек."""
    task_data = {
        "type": "edit_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_data": item_data.model_dump()
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}


@router.delete("/item/delete")
async def delete_item(request: Request,
                      uuid: UUID,
                      item_id: int,
                      user: User = Depends(get_current_user)):
    """Добавляет позицию в чек."""
    task_data = {
        "type": "delete_item_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "item_id": item_id
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для добавления отправлены в очередь"}