import os
from loguru import logger
from dotenv import load_dotenv

from services.classifier_instance import get_classifier

load_dotenv()


async def classifier_image(file_location):
    """Обработка изображения с использованием классификатора"""
    try:
        if not os.path.exists(file_location):
            raise FileNotFoundError(f"File not found at location: {file_location}")

        classifier = get_classifier()
        result = await classifier.classify_image(file_location)
        logger.info(f"Image classification result: {result}")

        # Проверка на допустимость контента
        content_type = result["content_type"]
        if content_type != "Allowed Content":
            return content_type

        return content_type

    except Exception as e:
        error_message = f"Error processing image: {str(e)}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}


if __name__ == '__main__':
    pass
