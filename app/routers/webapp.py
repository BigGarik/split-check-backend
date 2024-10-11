import json
import os
from dotenv import load_dotenv
from loguru import logger

from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.auth import get_current_user, authenticate_user, create_token
from app.crud import get_user_by_email, create_new_user
from app.database import get_db
from app.models import User
from app.routers.ws import ws_manager
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
    logger.info(f"User {user_id} uploaded an image")
    # Запускаем процесс обработки изображения
    await upload_image_process(user_id, file)

    return {"message": "Файл успешно загружен. Обработка..."}


@router_webapp.post("/get_check")
async def get_value(key: str = Query(None), request: dict = None):
    if request and "key" in request:
        key = request["key"]

    if not key:
        raise HTTPException(status_code=400, detail="Key is required")

    # value = await redisManager.get_value(key)
    value = None
    logger.info(f"Retrieved value for key '{key}': {value}")

    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    response = json.loads(value)
    return response


@router_webapp.get("/check/{key}")
async def get_check(key: str):
    # value = await redisManager.get_value(key)
    value = None
    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    return json.loads(value)


@router_webapp.post("/check/inc")
async def increment_check_pos(current_user: User = Depends(get_current_user)):
    # current_user.id
    return {"status": "Message sent to all users"}


@router_webapp.post("/check/decr")
async def decrement_check_pos(current_user: User = Depends(get_current_user)):
    return {"status": "Message sent to all users"}

