import json
import logging
import re

from anthropic import Anthropic

from src.config.settings import settings
from .message import form_message

logger = logging.getLogger(__name__)

api_key = settings.api_key
claude_model_name = settings.claude_model_name

client = Anthropic(api_key=api_key)


async def recognize_check_by_anthropic(file_location_directory: str):
    prompt = ("""
        Внимательно изучи и распознай чек.
        Важно!!! В ответ пришли только данные в формате json без комментариев со структурой:
        {
          "restaurant": "Название заведения (если есть)",
          "address": "Адрес заведения (если есть)",
          "phone": "Телефон заведения (если есть)",
          "table_number": "Номер стола (если есть)",
          "order_number": "Номер заказа (если есть)",
          "date": "Дата (ДД.ММ.ГГГГ) (если есть)",
          "time": "Время (ЧЧ:ММ) (если есть)",
          "waiter": "Имя официанта (если есть)",
          "items": [
            {
              "id": порядковый_номер,
              "name": "Точное наименование",
              "quantity": количество,
              "sum": общая_сумма
            },
            // другие позиции
          ],
          "subtotal": промежуточный_итог,
          "service_charge": { // (если есть)
            "name": "Название сбора",
            "percentage": процент_сбора,
            "amount": сумма_сбора
          },
          "vat": { // (если есть)
            "rate": ставка_ндс,
            "amount": сумма_ндс
          },
          "discount": { // (если есть)
            "percentage": процент_скидки,
            "amount": сумма_скидки
          },
          "total": итоговая_сумма,
          "currency": валюта в ISO 4217 (если можно определить) иначе none
        }
    """)
    message = await form_message(file_location_directory, prompt=prompt)

    try:
        response = client.messages.create(
            model=claude_model_name,
            max_tokens=2048,
            messages=message
        )
        logger.info(f"Response: {response.content[0].text}")
        response_text = response.content[0].text

        # Используем регулярное выражение для поиска блока, начинающегося с фигурной скобки и заканчивающегося на фигурную
        # Флаг re.DOTALL позволяет точке '.' захватывать символы перевода строки
        pattern = r'(\{.*\})'
        match = re.search(pattern, response_text, re.DOTALL)

        if match:
            json_str = match.group(1)  # Извлекаем найденный JSON-блок в виде строки
            # Парсим JSON-строку в объект Python (например, словарь)
            data = json.loads(json_str)
            logger.info(f"Извлечённый и распарсенный JSON: {data}")
            return data
        else:
            logger.error("JSON не найден в строке")

    except json.JSONDecodeError as e:
        # Обработка ошибок, если строка не является корректным JSON
        logger.error(f"Ошибка при декодировании JSON: {e}")
    except Exception as e:
        logger.error(f"Ошибка при декодировании JSON: {e}")
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
