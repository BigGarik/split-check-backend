from fastapi import APIRouter, Query
from fastapi import File, UploadFile, Depends
from loguru import logger

from app.auth import get_current_user
from app.crud import add_or_update_user_selection, join_user_to_check
from app.models import User
from app.redis import queue_processor
from app.schemas import CheckSelectionRequest
from app.utils import upload_image_process

router = APIRouter(prefix="/check", tags=["check"])


@router.post("/upload-image")
async def upload_image(
        user: User = Depends(get_current_user),
        file: UploadFile = File(...),
):
    # Запускаем процесс обработки изображения
    task_data = await upload_image_process(user.id, file)
    # Отправляем данные для обработки в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Файл успешно загружен. Обработка..."}


@router.get("/all")
async def get_all_check(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    task_data = {
        "type": "send_all_checks",
        "user_id": user.id,
        "page": page,
        "page_size": page_size
    }
    # Отправляем параметры пагинации в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Данные чеков отправлены в очередь для передачи через WebSocket"}


@router.get("/{uuid}")
async def get_check(uuid: str, user: User = Depends(get_current_user)):
    # check_data = await get_check_data_by_uuid(uuid)
    # participants, _ = await get_user_selection_by_check_uuid(uuid)
    # # Если данных нет и в БД, выбрасываем исключение
    # if not check_data:
    #     raise HTTPException(status_code=404, detail="Check not found")

    task_data = {
        "type": "send_check_data",
        "user_id": user.id,
        "check_uuid": uuid,
    }

    # Отправляем данные чека в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.post("{uuid}/select")
async def user_selection(uuid: str,
                         selection: CheckSelectionRequest,
                         user: User = Depends(get_current_user)):

    await add_or_update_user_selection(user_id=user.id, check_uuid=uuid, selection_data=selection)
    # Отправляем данные чека в очередь Redis
    task_data = {
        "type": "send_check_selection",
        "user_id": user.id,
        "check_uuid": uuid,
    }
    logger.info(selection.dict())
    await queue_processor.push_task(task_data)

    return {"message": "Данные о выборе отправлены в очередь для передачи через WebSocket"}


@router.post("/join")
async def join_check(
    uuid: str,
    user: User = Depends(get_current_user)
):
    """Присоединяет пользователя к чеку."""
    await join_user_to_check(user.id, uuid)
    return {
        "status": "success",
        "message": "User joined to the check successfully"
    }
