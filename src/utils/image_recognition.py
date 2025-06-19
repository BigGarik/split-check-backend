import json
import logging
import re
from typing import Optional, Dict, Any

from src.config import config

logger = logging.getLogger(config.app.service_name)


def is_valid_json_response(response_text: str) -> bool:
    """
    Проверяет, содержит ли ответ валидный JSON блок.

    Args:
        response_text: Текст ответа от API

    Returns:
        True если найден валидный JSON, False в противном случае
    """
    pattern = r'(\{.*\})'
    match = re.search(pattern, response_text, re.DOTALL)

    if not match:
        return False

    try:
        json.loads(match.group(1))
        return True
    except json.JSONDecodeError:
        return False


def extract_json_from_response(response_text: str) -> Optional[Dict[Any, Any]]:
    """
    Извлекает и парсит JSON из ответа API.

    Args:
        response_text: Текст ответа от API

    Returns:
        Словарь с данными или None в случае ошибки
    """
    pattern = r'(\{.*\})'
    match = re.search(pattern, response_text, re.DOTALL)

    if match:
        try:
            json_str = match.group(1)
            data = json.loads(json_str)
            logger.info("JSON успешно извлечён и распарсен")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при декодировании JSON: {e}")
            return None
    else:
        logger.error("JSON не найден в ответе")
        return None