import json

from dotenv import load_dotenv
from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.redis import queue_processor, redis_client
from app.utils import upload_image_process

load_dotenv()

router_webapp = APIRouter()


@router_webapp.post("/upload-image/")
async def upload_image(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
):
    user_id = current_user.email
    # Запускаем процесс обработки изображения
    task_data = await upload_image_process(user_id, file)
    # Отправляем данные для обработки в очередь Redis
    await queue_processor.push_task(task_data)

    return {"message": "Файл успешно загружен. Обработка..."}


@router_webapp.post("/get_check")
async def get_value(key: str = Query(None), request: dict = None):
    if request and "key" in request:
        key = request["key"]

    if not key:
        raise HTTPException(status_code=400, detail="Key is required")

    # value = await redisManager.get_value(key)
    value = None

    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    response = json.loads(value)
    return response


@router_webapp.get("/check/{uuid}")
async def get_check(uuid: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Ищем данные чека в Redis по uuid
    redis_key = f"check_uuid_{uuid}"
    check_data = await redis_client.get(redis_key)

    if not check_data:
        # Если данных нет в Redis, можно попробовать найти их в базе данных
        # Здесь должна быть логика поиска в БД
        # Пример: check_data = db.query(Check).filter(Check.uuid == uuid).first()
        # Если данных нет и в БД, выбрасываем исключение
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


@router_webapp.post("/check/inc")
async def increment_check_pos(current_user: User = Depends(get_current_user)):
    # current_user.id
    return {"status": "Message sent to all users"}


@router_webapp.post("/check/decr")
async def decrement_check_pos(current_user: User = Depends(get_current_user)):
    return {"status": "Message sent to all users"}

