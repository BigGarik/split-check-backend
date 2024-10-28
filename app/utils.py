import os
import uuid

from dotenv import load_dotenv
from fastapi import UploadFile
from sqlalchemy import insert

from app.crud import get_user_by_id
from app.database import get_async_db
from app.models import user_check_association, Check

load_dotenv()

upload_directory = os.getenv('UPLOAD_DIRECTORY')


async def get_all_checks(user_id: int) -> list[str]:
    user = await get_user_by_id(user_id)
    if user:
        return [check.uuid for check in user.checks]
    return []


async def upload_image_process(user_id: int, file: UploadFile):
    """ 1. метод загрузки фото
            1.1 генерация uuid
            1.2 создание папки/или имя файла с таким uuid
            1.3 сохранить изображение в этой папке/под таким именем
            1.4 сформировать сообщение для отправки в очередь, например можно сделать структуру
            {
                "type":"recognize_image",
                "user_id":user_id,
                "payload":{"file_name/folder":uuid}
            }
            и отправить в очередь пока предлагаю в общую, потом можно разнести
    """
    check_uuid = str(uuid.uuid4())

    # Создаем директорию, если она не существует
    directory = os.path.join(upload_directory, check_uuid)
    os.makedirs(directory, exist_ok=True)

    # Сохраняем файл

    file_name = file.filename
    file_location = os.path.join(directory, file_name)

    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    task_data = {
        "type": "recognize_image",
        "user_id": user_id,
        "payload": {
            "check_uuid": check_uuid,
            "file_location_directory": directory,
            "file_name": file_name,
        }
    }

    return task_data


if __name__ == '__main__':
    pass
