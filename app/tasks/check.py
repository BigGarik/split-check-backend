import json
import os
import uuid
from datetime import datetime

from loguru import logger
from dotenv import load_dotenv

from app.crud import add_check_to_database
from app.routers.ws import ws_manager

load_dotenv()


async def add_empty_check_task(user_id: int):
    check_uuid = str(uuid.uuid4())

    check_json = {
        "restaurant": "",
        "table_number": "",
        "order_number": "",
        "date": datetime.now().strftime("%d.%m.%Y"),
        "time": datetime.now().strftime("%H:%M"),
        "waiter": "",
        "items": [],
        "subtotal": 0,
        "service_charge": {
            "name": "",
            "amount": 0
        },
        "vat": {
            "rate": 0,
            "amount": 0
        },
        "total": 0
    }
    logger.debug(check_json)
    await add_check_to_database(check_uuid, user_id, check_json)

    msg = {
        "type": "checkAddEvent",
        "payload": {
            "uuid": check_uuid,
        },
    }
    msg_to_ws = json.dumps(msg)
    await ws_manager.send_personal_message(msg_to_ws, user_id)


if __name__ == '__main__':
    pass
