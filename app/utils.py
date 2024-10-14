# utils.py

import json
import os
import uuid
from loguru import logger
from dotenv import load_dotenv


load_dotenv()

upload_directory = os.getenv('UPLOAD_DIRECTORY')


async def upload_image_process(user_id, file):
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

    # Сохраняем файл
    file_location = f"{upload_directory}/{check_uuid}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    task_data = {
        "type": "recognize_image",
        "user_id": user_id,
        "payload": {
            "check_uuid": check_uuid,
            "file_location": file_location
        }
    }

    return task_data


if __name__ == '__main__':
    pass
