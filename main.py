import logging
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from service.system import get_base64_encoded_image

load_dotenv()
logger = logging.getLogger(__name__)
api_key = os.getenv("API_KEY")


client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-sonnet-20240620"


message_list = [
    {
        "role": 'user',
        "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/JPEG", "data": get_base64_encoded_image("IMG_0833.JPEG")}},
            # {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": get_base64_encoded_image("../images/best_practices/receipt2.png")}},
            {"type": "text", "text": "Распознай чек. пришли ответ со структурой: номер позиции, наименование, количество, цена, сумма. Итого сумма чека. в отвт пришли только распознанные данные"}
        ]
    }
]

response = client.messages.create(
    model=MODEL_NAME,
    max_tokens=2048,
    messages=message_list
)
print(response.content[0].text)


if __name__ == '__main__':
    pass
