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

UPLOAD_DIRECTORY = "images"

access_secret_key = os.getenv('ACCESS_SECRET_KEY')
refresh_secret_key = os.getenv('REFRESH_SECRET_KEY')
algorithm = os.getenv('ALGORITHM')
access_token_expire_minutes = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
refresh_token_expire_days = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS'))


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
    # Отправляем сообщение пользователю через WebSocket, если он подключен
    # await ws_manager.send_personal_message("Ваше изображение обрабатывается.", user_id)

    return {"message": "Файл успешно загружен. Обработка..."}


# @router_webapp.post("/upload-image/")
# async def upload_image(file: UploadFile = File(...)):
#     if not file:
#         return JSONResponse(content={"message": "No file sent"}, status_code=400)
#
#     if not file.content_type.startswith("image/"):
#         return JSONResponse(content={"message": "File is not an image"}, status_code=400)
#
#     if not os.path.exists(upload_directory):
#         os.makedirs(upload_directory)

#     uuid_dir = uuid.uuid4()
#     upload_directory = os.path.join(UPLOAD_DIRECTORY, str(uuid_dir))
#     file_path = os.path.join(upload_directory, file.filename)
#
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
#     response = recognize_check(upload_directory)
#
#     # Данные для сохранения в Redis
#     redis_data = {
#         "message": f"Successfully uploaded {file.filename}",
#         "response": response
#     }
#
#     # Сериализуем данные в JSON
#     json_data = json.dumps(redis_data)
#
#     # Сохраняем данные в Redis
#     uuid_str = str(uuid_dir)
#     await redis_client.set(uuid_str, json_data)
#
#     # Устанавливаем время жизни ключа (например, 1 час = 3600 секунд)
#     await redis_client.expire(uuid_str, 3600 * 24)
#
#     response_data = {
#         "message": f"Successfully uploaded {file.filename}",
#         "uuid": uuid_str,
#         "response": response
#     }
#
#     final_json_string = json.dumps(response_data, ensure_ascii=False, indent=2)
#     logger.info(final_json_string)
#     return JSONResponse(content=final_json_string, status_code=200)


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


@router_webapp.post("/user/create", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = create_new_user(db=db, user=user)
    return new_user


# Эндпоинт для получения access_token и refresh_token
@router_webapp.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Аутентификация пользователя
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. Создаем Access и Refresh токены
    access_token = create_token(data={"sub": user.email},
                                token_expire_minutes=access_token_expire_minutes,
                                secret_key=access_secret_key)
    refresh_token = create_token(data={"sub": user.email},
                                 token_expire_minutes=refresh_token_expire_days,
                                 secret_key=refresh_secret_key)

    # 3. Возвращаем токены
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
