import logging
import os

from src.config import config
from src.services.classifier.classifier_instance import get_classifier

logger = logging.getLogger(config.app.service_name)


async def classifier_image(file_location):
    """Обработка изображения с использованием классификатора"""
    try:
        if not os.path.exists(file_location):
            raise FileNotFoundError(f"File not found at location: {file_location}")

        classifier = get_classifier()
        result = await classifier.classify_image(file_location)
        logger.debug(f"Image classification result: {result}")

        # Проверка на допустимость контента
        content_type = result["content_type"]
        if content_type != "Allowed Content":
            return content_type

        return content_type

    except Exception as e:

        logger.error(f"Error processing image: {str(e)}")
        return {"status": "error", "message": f"Error processing image: {str(e)}"}
