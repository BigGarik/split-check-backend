from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Depends
from loguru import logger

from app.auth import get_current_user
from app.crud import add_or_update_user_selection, get_check_data_by_uuid
from app.models import User
from app.redis import queue_processor
from app.schemas import CheckSelectionRequest
from app.utils import upload_image_process

router_webapp = APIRouter()


@router_webapp.post("/upload-image/")
async def upload_image(
        user: User = Depends(get_current_user),
        file: UploadFile = File(...),
):
    user_id = user.id
    # Запускаем процесс обработки изображения
    task_data = await upload_image_process(user_id, file)
    # Отправляем данные для обработки в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Файл успешно загружен. Обработка..."}


@router_webapp.get("/checks")
async def get_all_check(user: User = Depends(get_current_user)):
    task_data = {
        "type": "send_all_checks",
        "user_id": user.id,
    }
    # Отправляем check_uuids в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Данные чеков отправлены в очередь для передачи через WebSocket"}


@router_webapp.get("/check/{uuid}")
async def get_check(uuid: str, user: User = Depends(get_current_user)):
    check_data = await get_check_data_by_uuid(uuid)
    # Если данных нет и в БД, выбрасываем исключение
    if not check_data:
        raise HTTPException(status_code=404, detail="Check not found")

    task_data = {
        "type": "send_check_data",
        "user_id": user.id,
        "check_uuid": uuid,
        "check_data": check_data
    }

    # Отправляем данные чека в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Check data has been sent to WebSocket queue"}


@router_webapp.post("/check/{uuid}/select")
async def user_selection(uuid: str,
                         selection: CheckSelectionRequest,
                         user: User = Depends(get_current_user)):

    await add_or_update_user_selection(user_id=user.id, check_uuid=uuid, selection_data=selection)
    # Отправляем данные чека в очередь Redis
    task_data = {
        "type": "send_check_selection",
        "check_uuid": uuid,
    }
    logger.info(selection.dict())
    await queue_processor.push_task(task_data)

    return {"message": "Check selection data has been sent to WebSocket queue"}
