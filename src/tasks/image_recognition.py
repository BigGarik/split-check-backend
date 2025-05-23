import json
import os

from fastapi import Depends
import logging

from src.config import ENVIRONMENT
from src.config.type_events import Events
from src.utils.system import get_memory_usage
from src.websockets.manager import ws_manager
from src.managers.check_manager import CheckManager, get_check_manager
from src.services.ai.api_anthropic import recognize_check_by_anthropic
from src.services.classifier.classifier_image import classifier_image


logger = logging.getLogger(__name__)


def calculate_price(json_data):
    """
    Вычисляет и записывает цену для каждого элемента в JSON.
    Перезаписывает price, если он уже есть.
    Считает quantity равным 1, если оно меньше 1.

    Args:
        json_data (dict): JSON данные.

    Returns:
        dict: JSON данные с добавленными ценами.
    """

    for item in json_data['items']:
        # Проверяем quantity и устанавливаем значение 1, если оно меньше 1
        quantity = item['quantity']
        if quantity < 1:
            quantity = 1

        # Вычисляем и записываем цену
        item['price'] = item['sum'] / quantity

    return json_data


async def recognize_image_task(
        check_uuid: str,
        user_id: int,
        file_location_directory: str,
        file_name: str,
        check_manager: CheckManager = Depends(get_check_manager)
):
    """ Обработка изображения: классификация и распознавание. """

    image_path = os.path.join(file_location_directory, file_name)
    logger.info(f"Начало обработки изображения {image_path} для пользователя  {user_id}, память: {get_memory_usage():.2f} MB")

    try:
        # Классификация изображения
        classification_result = await classifier_image(image_path)
        if classification_result == "Allowed Content":
            # Распознавание чека
            if ENVIRONMENT == "prod":
                recognized_json = await recognize_check_by_anthropic(file_location_directory)
            else:
                recognized_json = {
                    "restaurant": "Bistro",
                    "table_number": "1",
                    "order_number": "998",
                    "date": "19.11.2024",
                    "time": "13:26",
                    "waiter": "Kacca 2",
                    "items": [
                        {
                            "id": 1,
                            "name": "Бабушкин хлеб",
                            "quantity": 2,
                            "sum": 4000
                        },
                        {
                            "id": 2,
                            "name": "Солянка",
                            "quantity": 1,
                            "sum": 16000
                        },
                        {
                            "id": 3,
                            "name": "Куриный суп с лапшой",
                            "quantity": 1,
                            "sum": 16000
                        },
                        {
                            "id": 4,
                            "name": "Говядина с грибами",
                            "quantity": 1,
                            "sum": 21000
                        },
                        {
                            "id": 5,
                            "name": "Рис отварной",
                            "quantity": 0.5,
                            "sum": 3500
                        },
                        {
                            "id": 6,
                            "name": "Гречка",
                            "quantity": 0.5,
                            "sum": 3000
                        },
                        {
                            "id": 7,
                            "name": "Ёжик из курицы",
                            "quantity": 1,
                            "sum": 12000
                        },
                        {
                            "id": 8,
                            "name": "Сендвич с курицей",
                            "quantity": 1,
                            "sum": 13000
                        }
                    ],
                    "subtotal": 88500,
                    "service_charge": {
                        "name": "",
                        "amount": 0
                    },
                    "vat": {
                        "rate": 0,
                        "amount": 0
                    },
                    "total": 88500
                }

            # calculate_price(recognized_json)

            logger.debug(f"Recognition completed for check_uuid {check_uuid}")

            await check_manager.add_check(user_id, check_uuid, recognized_json)

        else:
            error_msg = {
                "type": Events.IMAGE_RECOGNITION_EVENT_STATUS,
                "status": "error",
                "message": f"Image classification failed with result: {classification_result}"
            }
            msg_to_ws = json.dumps(error_msg)
            await ws_manager.send_personal_message(msg_to_ws, user_id)

            logger.warning(
                f"Image classification for check_uuid {check_uuid} failed with result: {classification_result}")
    except Exception as e:

        error_msg = {
            "type": Events.IMAGE_RECOGNITION_EVENT_STATUS,
            "status": "error",
            "message": f"Error processing image {check_uuid}: {e}"
        }
        msg_to_ws = json.dumps(error_msg)
        await ws_manager.send_personal_message(msg_to_ws, user_id)

        logger.error(f"Error processing image {check_uuid}: {e}")
    logger.info(f"Конец обработки изображения {image_path} для пользователя  {user_id}, память: {get_memory_usage():.2f} MB")
