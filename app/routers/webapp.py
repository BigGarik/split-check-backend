import json
import logging

from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import redis_client, get_db
from app.models import User
from app.nats import nats_client
from app.routers.ws import ws_manager
from external_services.tasks import recognize

router_webapp = APIRouter()

logger = logging.getLogger(__name__)


UPLOAD_DIRECTORY = "images"


@router_webapp.get("/test/")
def test():
    print("Hello World")
    return {"message": "Hello World"}


@router_webapp.post("/upload-image/")
async def upload_image(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
):
    user_id = current_user.email
    prefix = "ws_connections:"
    session_id = await redis_client.get(f"{prefix}{user_id}")
    print(f"session_id: {session_id}")
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    # Сохраняем файл
    file_location = f"images/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # Добавляем задачу в очередь Celery
    task = recognize.delay(session_id)
    print(f"task_id: {task.id}")

    return {"task_id": task.id, "message": "File uploaded successfully, processing..."}


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


@router_webapp.get("/get_check")
@router_webapp.post("/get_check")
async def get_value(key: str = Query(None), request: dict = None):
    if request and "key" in request:
        key = request["key"]

    if not key:
        raise HTTPException(status_code=400, detail="Key is required")

    value = await redis_client.get(key)
    logger.info(f"Retrieved value for key '{key}': {value}")

    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    response = json.loads(value)
    return response


# Маршрут для отправки сообщения конкретному пользователю
@router_webapp.post("/send-message/{user_id}")
async def send_message_to_user(user_id: str, message: str):
    await ws_manager.send_personal_message(message, user_id)
    return {"message": f"Message sent to {user_id}"}


# Маршрут для отправки сообщения всем подключенным пользователям
@router_webapp.post("/broadcast")
async def broadcast_message(message: str):
    await ws_manager.broadcast(message)
    return {"message": "Message broadcasted to all users"}


@router_webapp.post("/update")
async def broadcast_message_to_all(message: str):
    """
    Отправляет сообщение в топик 'broadcast' в NATS. Все WebSocket-подключения его получат.
    """
    # Отправляем сообщение в NATS в топик 'broadcast'
    await nats_client.publish("broadcast", message.encode())
    return {"status": "Message sent to all users"}
