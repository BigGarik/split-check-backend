import logging
import os

from anthropic import Anthropic
from dotenv import load_dotenv

from service.system import get_base64_encoded_image, convert_img, form_message

load_dotenv()
logger = logging.getLogger(__name__)
api_key = os.getenv("API_KEY")

client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-sonnet-20240620"


def recognize_check():
    prompt = "Распознай чек. пришли ответ со структурой: номер позиции, наименование, количество, цена, сумма. Итого сумма чека. в отвт пришли только распознанные данные"
    message = form_message("images", prompt=prompt)

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=2048,
        messages=message
    )
    print(response.content[0].text)


if __name__ == '__main__':
    recognize_check()
