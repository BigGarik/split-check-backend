import json
import logging
import os
from redis import asyncio as aioredis
import shutil
import uuid
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from external_services.api_anthropic import recognize_check


logger = logging.getLogger(__name__)

app = FastAPI()


redis_client = aioredis.from_url("redis://localhost", encoding="utf8", decode_responses=True)

# app.include_router(webhook_router, prefix="/payment")


UPLOAD_DIRECTORY = "images"


@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    uuid_dir = uuid.uuid4()
    upload_directory = os.path.join(UPLOAD_DIRECTORY, str(uuid_dir))
    if not file:
        return JSONResponse(content={"message": "No file sent"}, status_code=400)

    if not file.content_type.startswith("image/"):
        return JSONResponse(content={"message": "File is not an image"}, status_code=400)

    if not os.path.exists(upload_directory):
        os.makedirs(upload_directory)

    file_path = os.path.join(upload_directory, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    response = recognize_check(upload_directory)

    # Данные для сохранения в Redis
    redis_data = {
        "message": f"Successfully uploaded {file.filename}",
        "response": response
    }

    # Сериализуем данные в JSON
    json_data = json.dumps(redis_data)

    # Сохраняем данные в Redis
    uuid_str = str(uuid_dir)
    await redis_client.set(uuid_str, json_data)

    # Устанавливаем время жизни ключа (например, 1 час = 3600 секунд)
    await redis_client.expire(uuid_str, 3600*24)

    response_data = {
        "message": f"Successfully uploaded {file.filename}",
        "uuid": uuid_str,
        "response": response
    }

    final_json_string = json.dumps(response_data, ensure_ascii=False, indent=2)
    logger.info(final_json_string)
    return JSONResponse(content=final_json_string, status_code=200)


@app.get("/get_check/{key}")
async def get_value(key: str):
    value = await redis_client.get(key)
    logger.info(value)
    if value is None:
        return {"message": "Key not found"}
    return {"value": value.decode("utf-8")}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
