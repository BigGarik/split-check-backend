import json

from app.database import get_async_db, async_engine
from app.routers.ws import ws_manager
from fastapi import HTTPException
from loguru import logger

from app.utils import get_all_checks


async def send_all_checks(user_id: int):
    check_uuids = await get_all_checks(user_id)
    msg = {
        "type": "allBillEvent",
        "payload": check_uuids
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


async def send_check_data(user_id, check_data: str):
    check_data = json.loads(check_data)
    msg = {
        "type": "billDetailEvent",
        "payload": check_data["payload"],
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")
    # Отправляем данные чека через WebSocket
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )

