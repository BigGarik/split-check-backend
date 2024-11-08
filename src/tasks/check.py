import json
import uuid
from datetime import datetime
from loguru import logger
from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.repositories.check import get_check_data_by_uuid, get_all_checks, add_check_to_database, \
    delete_association_by_check_uuid
from src.repositories.user_selection import get_user_selection_by_check_uuid
from src.services.user import join_user_to_check
from src.utils.notifications import create_event_message, create_event_status_message


async def send_check_data_task(user_id, check_uuid: str):
    check_data = await get_check_data_by_uuid(check_uuid)

    logger.debug(f"Получили данные чека: {check_data}")

    participants, _ = await get_user_selection_by_check_uuid(check_uuid)

    participants = json.loads(participants)
    logger.debug(f"Получили список participants: {participants}")

    check_data["participants"] = participants

    msg_check_data = create_event_message(message_type=settings.Events.BILL_DETAIL_EVENT, payload=check_data)

    logger.debug(f"Отправляем сообщение: {json.dumps(msg_check_data, ensure_ascii=False)}")

    # Отправляем данные чека через WebSocket
    await ws_manager.send_personal_message(
        message=json.dumps(msg_check_data),
        user_id=user_id
    )


async def send_all_checks_task(user_id: int, page: int = 1, page_size: int = 10):

    checks_data = await get_all_checks(user_id, page, page_size)

    msg = create_event_message(message_type=settings.Events.ALL_BILL_EVENT,
                               payload={
                                   "checks": checks_data["items"],
                                   "pagination": {
                                       "total": checks_data["total"],
                                       "page": checks_data["page"],
                                       "pageSize": checks_data["page_size"],
                                       "totalPages": checks_data["total_pages"]
                                   }
                               }
                               )

    logger.debug(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")

    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


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
        "type": settings.Events.CHECK_ADD_EVENT,
        "payload": {
            "uuid": check_uuid,
        },
    }
    msg_to_ws = json.dumps(msg)
    await ws_manager.send_personal_message(msg_to_ws, user_id)


async def join_check_task(user_id: int, check_uuid: str):
    try:
        await join_user_to_check(user_id, check_uuid)

        status_message = create_event_status_message(message_type=settings.Events.JOIN_BILL_EVENT_STATUS,
                                                     status="success")

        await ws_manager.send_personal_message(
            message=json.dumps(status_message),
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при присоединении к чеку: {str(e)}")

        error_message = create_event_status_message(message_type=settings.Events.JOIN_BILL_EVENT_STATUS,
                                                    status="error",
                                                    message=str(e))

        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )


async def delete_check_task(user_id: int, check_uuid: str):
    try:
        await delete_association_by_check_uuid(check_uuid, user_id)
        status_message = create_event_status_message(message_type=settings.Events.CHECK_DELETE_EVENT_STATUS,
                                                     status="success")
        await ws_manager.send_personal_message(
            message=json.dumps(status_message),
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при разделении позиции: {str(e)}")
        # Обработка ошибки для инициатора
        error_message = create_event_status_message(message_type=settings.Events.CHECK_DELETE_EVENT_STATUS,
                                                    status="error",
                                                    message=str(e))
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
