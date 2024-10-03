import json
import logging
import uuid

from fastapi import APIRouter
from fastapi import File, UploadFile, HTTPException, Query, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import schemas
from app.auth import get_current_user, authenticate_user, create_access_token
from app.crud import get_user_by_email
from app.database import get_db
from app.models import User
from external_services.tasks import recognize

router_webapp = APIRouter()

logger = logging.getLogger(__name__)

UPLOAD_DIRECTORY = "images"

@router_webapp.post("/upload-image/")
async def upload_image(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        file: UploadFile = File(...),
):
    user_id = current_user.email

    uuid_filename = uuid.uuid4()
    # Сохраняем файл
    file_location = f"images/{uuid_filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    # Добавляем задачу в очередь Celery
    task = recognize.delay(uuid_filename, user_id)
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



@router_webapp.post("/get_check")
async def get_value(key: str = Query(None), request: dict = None):
    if request and "key" in request:
        key = request["key"]

    if not key:
        raise HTTPException(status_code=400, detail="Key is required")


    #value = await redisManager.get_value(key)
    value = None
    logger.info(f"Retrieved value for key '{key}': {value}")

    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    response = json.loads(value)
    return response


@router_webapp.get("/check/{key}")
async def get_check(key: str):
    #value = await redisManager.get_value(key)
    value = None
    if value is None:
        return JSONResponse(content={"message": "Key not found"}, status_code=404)

    return json.loads(value)

@router_webapp.post("/check/inc")
async def increment_check_pos(current_user: User = Depends(get_current_user)):

    current_user.id



    # Отправляем сообщение в NATS в топик 'broadcast'
    # await nats_client.publish("broadcast", message.encode())
    return {"status": "Message sent to all users"}

@router_webapp.post("/check/decr")
async def decrement_check_pos(current_user: User = Depends(get_current_user)):


    # Отправляем сообщение в NATS в топик 'broadcast'
    # await nats_client.publish("broadcast", message.encode())
    return {"status": "Message sent to all users"}


@router_webapp.post("/user/create", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return create_user(db=db, user=user)


@router_webapp.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    print(user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.email})
    response = {"access_token": access_token, "token_type": "bearer"}
    return response
