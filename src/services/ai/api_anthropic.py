import json
import logging
from typing import Optional, Dict, Any

from anthropic import Anthropic

from src.config import API_KEY, CLAUDE_MODEL_NAME
from src.utils.image_recognition import is_valid_json_response, extract_json_from_response
from .message import form_message

logger = logging.getLogger(__name__)

api_key = API_KEY
claude_model_name = CLAUDE_MODEL_NAME

client = Anthropic(api_key=api_key)


async def send_request_to_anthropic(message: list, max_retries: int = 2) -> Optional[str]:
    """
    Отправляет запрос к Anthropic API с повторными попытками.

    Args:
        message: Подготовленное сообщение для API
        max_retries: Максимальное количество попыток (по умолчанию 2)

    Returns:
        Текст ответа или None в случае ошибки
    """
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=claude_model_name,
                max_tokens=2048,
                messages=message
            )

            response_text = response.content[0].text
            logger.info(f"Попытка {attempt + 1}: Получен ответ от API")

            # Проверяем, содержит ли ответ JSON
            if is_valid_json_response(response_text):
                return response_text
            else:
                logger.warning(f"Попытка {attempt + 1}: Ответ не содержит валидный JSON")
                if attempt < max_retries - 1:
                    logger.info(f"Повторная отправка запроса (попытка {attempt + 2})")
                    continue
                else:
                    logger.error("Исчерпаны все попытки получения валидного JSON")
                    return response_text  # Возвращаем последний ответ даже если он невалидный

        except Exception as e:
            logger.error(f"Попытка {attempt + 1}: Ошибка при отправке запроса: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Повторная отправка запроса (попытка {attempt + 2})")
                continue
            else:
                logger.error("Исчерпаны все попытки отправки запроса")
                return None

    return None


async def recognize_check_by_anthropic(file_location_directory: str) -> Optional[Dict[Any, Any]]:
    """
    Распознаёт чек с помощью Anthropic API.

    Args:
        file_location_directory: Путь к файлу чека

    Returns:
        Словарь с данными чека или None в случае ошибки
    """

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
          "service_charge": {
            "name": "Название сбора",
            "percentage": процент_сбора,
            "amount": сумма_сбора
          },
          "vat": {
            "rate": ставка_ндс,
            "amount": сумма_ндс
          },
          "discount": {
            "percentage": процент_скидки,
            "amount": сумма_скидки
          },
          "total": итоговая_сумма,
          "currency": валюта в ISO 4217 (если можно определить) иначе none
        }
    """)

    try:
        # Формируем сообщение для API
        message = await form_message(file_location_directory, prompt=prompt)

        # Отправляем запрос с повторными попытками
        response_text = await send_request_to_anthropic(message, max_retries=2)

        if response_text is None:
            logger.error("Не удалось получить ответ от API")
            return None

        # Извлекаем и парсим JSON из ответа
        data = extract_json_from_response(response_text)

        if data:
            logger.info("Чек успешно распознан")
            return data
        else:
            logger.error("Не удалось извлечь данные чека")
            return None

    except Exception as e:
        logger.error(f"Неожиданная ошибка при распознавании чека: {e}")
        return None
    finally:
        # Очищаем переменные
        if 'message' in locals():
            del message


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
