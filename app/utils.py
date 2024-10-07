# utils.py

import json
import logging
import os
import uuid

from dotenv import load_dotenv

from app.redis import redis_queue_publish

load_dotenv()
logger = logging.getLogger(__name__)

upload_directory = os.getenv('UPLOAD_DIRECTORY')


async def upload_image_process(user_id, file):
    """ 1. метод загрузки фото
            1.1 генерация uuid
            1.2 создание папки/или имя файла с таким uuid
            1.3 сохранить изображение в этой папке/под таким именем
            1.4 сформировать сообщение для отправки в очередь, например можно сделать структуру
            {
                "type":"image_recognition",
                "user_id":user_id,
                "payload":{"file_name/folder":uuid}
            }
            и отправить в очередь пока предлагаю в общую, потом можно разнести
    """
    check_uuid = uuid.uuid4()

    # Сохраняем файл
    file_location = f"{upload_directory}/{check_uuid}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())

    msg = {
        "type": "image_recognition",
        "user_id": user_id,
        "payload": {
            "check_uuid": check_uuid,
            "file_location": file_location
        }
    }
    str_msg = json.dumps(msg)
    await redis_queue_publish(str_msg)


# 2. консьюмер очереди добавить метод recognize_Image, который принимает user_id, uuid
#     2.1 метод генерит статический json, кладет этот json в redis с ключом check_uuid_<uuid> и возвращает json
#     {"type":"image_recognition",
#     "target_user_id":user_id,
#     "payload":{"check_uuid ":check_uuid } }
#
# 3. Нужен API метод, который принимает параметр check_uuid и возвращает json из redis,
# потом сделаем чтобы метод если не находил значение в redis запрашивал его в БД, клал в redis и потом возвращал его
#


if __name__ == '__main__':
    pass
