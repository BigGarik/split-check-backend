import json
from app.routers.ws import ws_manager
from fastapi import HTTPException
from loguru import logger


async def send_all_checks(user_id):
    # Реализация логики отправки всех чеков
    logger.info(f"Sending all checks for user {user_id}")


async def send_check_data(user_id: str, check_data: str):
    check_data = json.loads(check_data)
    check_data_payload = json.dumps(check_data["payload"])
    logger.info(check_data_payload)
    # Отправляем данные чека через WebSocket
    await ws_manager.send_personal_message(
        message=check_data_payload,
        user_id=user_id
    )

