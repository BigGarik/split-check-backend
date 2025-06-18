import logging
from typing import Optional, Dict, Any

from openai import AsyncOpenAI

from src.config import config
from src.services.ai.prompt import prompt
from src.utils.image_recognition import is_valid_json_response, extract_json_from_response
from .message import message_for_anthropic

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=config.ai.openai_api_key.get_secret_value())


async def send_request_to_openai(message: list, max_retries: int = 2) -> Optional[str]:
    """
    Отправляет запрос к OpenAI API с повторными попытками.

    Args:
        message: Подготовленное сообщение в формате [{"role": "system"|"user"|"assistant", "content": "..."}]
        max_retries: Максимальное количество попыток

    Returns:
        Текст ответа или None
    """
    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=config.ai.openai_model_name,
                messages=message
            )

            response_text = response.choices[0].message.content.strip()
            logger.info(f"Попытка {attempt + 1}: Получен ответ от OpenAI: {response_text}")

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


async def recognize_check_by_openai(file_location_directory: str) -> Optional[Dict[Any, Any]]:
    """
    Распознаёт чек с помощью OpenAI API.

    Args:
        file_location_directory: Путь к файлу чека

    Returns:
        Словарь с данными чека или None
    """
    try:
        message = await message_for_anthropic(file_location_directory, prompt=prompt)
        response_text = await send_request_to_openai(message, max_retries=2)

        if response_text is None:
            logger.error("Не удалось получить ответ от OpenAI API")
            return None

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
        if 'message' in locals():
            del message


if __name__ == '__main__':
    pass
