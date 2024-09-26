import base64
import io
import json
import logging
import os
import random

from PIL import Image
from anthropic import Anthropic
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from app.celery_app import celery_app
from app.routers.ws import ws_manager

load_dotenv()
logger = logging.getLogger(__name__)
api_key = os.getenv("API_KEY")

client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-sonnet-20240620"


def form_message(image_folder, prompt=""):
    images = []
    print(image_folder)
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif')):
            img_path = os.path.join(image_folder, filename)
            with Image.open(img_path) as img:
                # Определяем текущие размеры
                width, height = img.size
                short_side = 1024
                # Определяем, какая сторона короче
                if width < height:
                    new_width = short_side
                    new_height = int(height * (short_side / width))
                else:
                    new_height = short_side
                    new_width = int(width * (short_side / height))

                # Изменяем размер изображения с сохранением пропорций
                img = img.resize((new_width, new_height), Image.LANCZOS)
                # Конвертируем изображение в RGB, если это необходимо
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                # Преобразуем изображение в байты
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                # img.save(('../images/' + filename), format="JPEG")
                img_bytes = buffer.getvalue()
                # Кодируем байты в base64
                base64_data = base64.b64encode(img_bytes).decode('utf-8')
                images.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64_data
                    }
                })

    return [
        {
            "role": "user",
            "content": [
                *images,
                {
                    "type": "text",
                    "text": prompt
                },
            ]
        }
    ]


@celery_app.task
async def recognize(session_id: str):
    recognized_json = {
        "restaurant": "Веранда",
        "table_number": "110",
        "order_number": "57",
        "date": "17.08.2024",
        "time": "17:28",
        "waiter": "Нурсултан А.",
        "items": [
            {
                "id": 1,
                "name": "Мохито 300 мл б/а",
                "quantity": 1,
                "price": 65000
            },
            {
                "id": 2,
                "name": "Вода Chortog 750мл без газа холодный",
                "quantity": 1,
                "price": 38000
            },
            {
                "id": 3,
                "name": "Paulaner",
                "quantity": 2,
                "price": 330000
            },
            {
                "id": 4,
                "name": "пиво Eggenberg Freibie г 330 мл",
                "quantity": 2,
                "price": 190000
            },
            {
                "id": 5,
                "name": "Ризотто с трюфелем",
                "quantity": 1,
                "price": 186000
            },
            {
                "id": 6,
                "name": "Наггетсы из индейки 5 шт",
                "quantity": 2,
                "price": 144000
            },
            {
                "id": 7,
                "name": "Картофель фри",
                "quantity": 1,
                "price": 45000
            },
            {
                "id": 8,
                "name": "Суши лосось",
                "quantity": 6,
                "price": 270000
            },
            {
                "id": 9,
                "name": "Кейк-попс с декором",
                "quantity": 2,
                "price": 70000
            },
            {
                "id": 10,
                "name": "Пицца с грушей с горго нзолой",
                "quantity": 1,
                "price": 155000
            },
            {
                "id": 11,
                "name": "Чай Ассам",
                "quantity": 1,
                "price": 45000
            },
            {
                "id": 12,
                "name": "Лимон добавка",
                "quantity": 1,
                "price": 12000
            },
            {
                "id": 13,
                "name": "Куриная котлета с гарн иром картофельное пюре",
                "quantity": 1,
                "price": 84000
            },
            {
                "id": 14,
                "name": "Макаронс малина",
                "quantity": 2,
                "price": 50000
            },
            {
                "id": 15,
                "name": "Макаронс шоколад",
                "quantity": 3,
                "price": 75000
            },
            {
                "id": 16,
                "name": "Вода Chortog 750мл без газа холодный",
                "quantity": 1,
                "price": 38000
            },
            {
                "id": 17,
                "name": "кетчуп добавка",
                "quantity": 1,
                "price": 20000
            }
        ],
        "subtotal": 1817000,
        "service_charge": {
            "name": "Сервисный сбор 12%",
            "amount": 218040
        },
        "vat": {
            "rate": 0,
            "amount": 0
        },
        "total": 2035040
    }
    response_data = {
        "message": f"Successfully uploaded image.jpg",
        "uuid": "9d0dd3fc-86e1-401a-bf0e-9f2d511b2442",
        "recognized_json": recognized_json
    }

    number = random.randrange(1, 11)
    import time
    time.sleep(10)  # Симуляция длительной обработки

    if number < 4:
        result = JSONResponse(content={"message": f"random {number}. No file response"}, status_code=400)
        ws_manager.send_personal_message(result, session_id)
        return response_data
    else:
        result = JSONResponse(content=response_data, status_code=200)
        ws_manager.send_personal_message(result, session_id)
        return result


def recognize_check(image_folder):
    prompt = (
        #
        # 'You have perfect vision and a keen eye for detail, making you an expert at recognizing information on cash register receipts. '
        # 'What information is on this receipt? '
        # 'Before you provide your answer in <answer> tags in the json format, think step by step in <thinking> tags and analyze each part of the cash register receipt.'

        "Внимательно изучи и распознай чек."
        "Пришли ответ со структурой: номер позиции, наименование, количество, цена, сумма."
        "Итого сумма чека. Проверь, что сумма всех позиций равна итоговой сумме."
        "В ответ пришли только данные в формате json без комментариев со структурой:"
        '{'
        '"items": ['
        '{'
        '"position": 1,'
        '"name": "Название товара",'
        '"quantity": 2,'
        '"price": 40000,'
        '"sum": 80000'
        '}'
        '],'
        '"total": 80000'
        '}'
    )
    message = form_message(image_folder, prompt=prompt)

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=message
    )
    print(response.content[0].text)
    # response_data = json.loads(response.content[0].text)
    try:
        response = json.loads(response.content[0].text)
        return response
    except Exception as e:
        logger.error(e)
        return None
    # return response.content[0].text


def test_claude():

    message = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "prompt"
                },
            ]
        }
    ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=message
    )
    # print(response.content[0].text)
    # response_data = json.loads(response.content[0].text)
    return json.loads(response.content[0].text)


if __name__ == '__main__':

    print(recognize_check("../images/f2c63269-7faa-4e33-ae81-15da4dc3b65e"))
