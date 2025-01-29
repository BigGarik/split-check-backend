import json
from anthropic import Anthropic
from loguru import logger

from src.config.settings import settings
from .message import form_message


api_key = settings.api_key
claude_model_name = settings.claude_model_name

client = Anthropic(api_key=api_key)


async def recognize_check_by_anthropic(file_location_directory: str):
    prompt = (
        # 'You have perfect vision and a keen eye for detail, making you an expert at recognizing information on cash register receipts. '
        # 'What information is on this receipt? '
        # 'Before you provide your answer in <answer> tags in the json format, think step by step in <thinking> tags and analyze each part of the cash register receipt.'

        "Внимательно изучи и распознай чек."
        "Пришли ответ со структурой: номер позиции, наименование, количество, цена, сумма."
        "Итого сумма чека. Проверь, что сумма всех позиций равна итоговой сумме."
        "В ответ пришли только данные в формате json без комментариев со структурой:"
        '{'
          '"restaurant": "Веранда",'
          '"table_number": "110",'
          '"order_number": "57",'
          '"date": "17.08.2024",'
          '"time": "17:28",'
          '"waiter": "Нурсултан А.",'
          '"items": ['
           ' {'
              '"id": 1,'
              '"name": "Мохито 300 мл б/а",'
              '"quantity": 5,'
              '"price": 13000,'
              '"sum": 65000'
           ' }'
          '],'
          '"subtotal": 65000,'
          '"service_charge": {'
            '"name": "Сервисный сбор 12%",'
            '"amount": 7800'
          '},'
          '"vat": {'
            '"rate": 0,'
            '"amount": 0'
          '},'
          '"total": 72800'
        '}'
    )
    message = await form_message(file_location_directory, prompt=prompt)

    try:
        response = client.messages.create(
            model=claude_model_name,
            max_tokens=2048,
            messages=message
        )
        logger.info(f"Response: {response.content[0].text}")
        response_json = json.loads(response.content[0].text)
        return response_json
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error: {e}")
    except Exception as e:
        logger.error(f"Error with recognition request: {e}")
    return None


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
        model=claude_model_name,
        max_tokens=2048,
        messages=message
    )
    # response_data = json.loads(response.content[0].text)
    return json.loads(response.content[0].text)


if __name__ == '__main__':

    print(recognize_check_by_anthropic("../images/8e3e9dbe-b63f-4956-b73a-ce8ef067e5cc"))
