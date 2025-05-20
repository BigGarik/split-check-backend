import json
import logging
import time
from typing import Optional, Dict, Any

from anthropic import Anthropic

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL_NAME
from src.services.ai.prompt import prompt
from src.utils.image_recognition import is_valid_json_response, extract_json_from_response
from .message import message_for_anthropic

logger = logging.getLogger(__name__)


client = Anthropic(api_key=ANTHROPIC_API_KEY)


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
            # Start timer
            start_time = time.time()

            response = client.messages.create(
                model=ANTHROPIC_MODEL_NAME,
                max_tokens=2048,
                messages=message
            )

            # End timer
            end_time = time.time()
            elapsed_time = end_time - start_time

            response_text = response.content[0].text
            logger.info(f"Попытка {attempt + 1}: Время ответа: {elapsed_time:.2f} секунд. Получен ответ от API: {response_text}")

            # Проверяем, содержит ли ответ JSON
            if is_valid_json_response(response_text):
                return response_text
            else:
                logger.warning(f"Попытка {attempt + 1}: Ответ не содержит валидный JSON")
                if attempt < max_retries - 1:
                    logger.info(f"Повторная отправка запроса (попытка {attempt + 2})")
                    continue
                else:
                    logger.error(f"Исчерпаны все попытки получения валидного JSON. response_text: {response_text}")
                    return None

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
    try:
        # Формируем сообщение для API
        message = await message_for_anthropic(file_location_directory, prompt=prompt)

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


if __name__ == '__main__':
    # Start timer
    start_time = time.time()

    completion = recognize_check_by_anthropic("../images/d783c1e1-6802-4a4c-ad82-a0de3907fd9c")

    # End timer
    end_time = time.time()
    elapsed_time = end_time - start_time

    # Output result and time taken
    print("🧠 Recognition Output:")
    print(completion)
    print(f"\n⏱️ Time taken for recognition: {elapsed_time:.2f} seconds")
