from uuid import UUID

from fastapi import APIRouter, Query
from fastapi import Depends
from loguru import logger

from src.api.deps import get_current_user
from src.models import User
from src.redis import queue_processor
from src.schemas import AddItemRequest, DeleteItemRequest, EditItemRequest, CheckSelectionRequest, ItemRequest

router = APIRouter()


@router.post("/add")
async def add_empty_check(user: User = Depends(get_current_user)):

    task_data = {
        "type": "add_empty_check_task",
        "user_id": user.id
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.get("/all")
async def get_all_check(page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=20, ge=1, le=100),
                        user: User = Depends(get_current_user)):

    task_data = {
        "type": "send_all_checks_task",
        "user_id": user.id,
        "page": page,
        "page_size": page_size
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чеков отправлены в очередь для передачи через WebSocket"}


@router.get("/main_page")
async def get_all_check(user: User = Depends(get_current_user)):

    task_data = {
        "type": "send_main_page_checks_task",
        "user_id": user.id,
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные главной страницы отправлены в очередь для передачи через WebSocket"}


@router.get("/{uuid}")
async def get_check(uuid: UUID,
                    user: User = Depends(get_current_user)):

    task_data = {
        "type": "send_check_data_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.post("/{uuid}/select")
async def user_selection(uuid: UUID,
                         selection: CheckSelectionRequest,
                         user: User = Depends(get_current_user)):

    task_data = {
        "type": "user_selection_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "selection_data": selection.model_dump()
    }
    await queue_processor.push_task(task_data)

    return {"message": "Данные о выборе отправлены в очередь для передачи через WebSocket"}


@router.post("/join")
async def join_check(uuid: UUID,
                     user: User = Depends(get_current_user)):
    """Присоединяет пользователя к чеку и возвращает статус операции."""
    task_data = {
        "type": "join_check_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для присоединения отправлены в очередь"}


@router.delete("/delete")
async def delete_check(uuid: UUID,
                       user: User = Depends(get_current_user)):
    """Удаляет чек."""
    task_data = {
        "type": "delete_check_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для удаления отправлены в очередь"}
