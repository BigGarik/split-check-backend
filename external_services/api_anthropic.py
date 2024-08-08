import base64
import io
import json
import logging
import os

from PIL import Image
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
api_key = os.getenv("API_KEY")

client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-sonnet-20240620"


def form_message(image_folder, prompt=""):
    images = []
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
                img.save(('../images/' + filename), format="JPEG")
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
                {
                    "type": "text",
                    "text": prompt
                },
                *images
            ]
        }
    ]


def recognize_check(image_folder):
    prompt = (
        #
        # 'You have perfect vision and a keen eye for detail, making you an expert at recognizing information on cash register receipts. '
        # 'What information is on this receipt? '
        # 'Before you provide your answer in <answer> tags in the json format, think step by step in <thinking> tags and analyze each part of the cash register receipt.'

        "Распознай чек. Пришли ответ со структурой: номер позиции, наименование, количество, цена, сумма. "
        "Итого сумма чека. В ответ пришли только данные в формате json со структурой:"
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
    # print(response.content[0].text)
    # response_data = json.loads(response.content[0].text)
    return json.loads(response.content[0].text)


if __name__ == '__main__':

    print(recognize_check("../images/f2c63269-7faa-4e33-ae81-15da4dc3b65e"))
