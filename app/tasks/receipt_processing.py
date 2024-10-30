import json

from loguru import logger

from app.crud import get_user_selection_by_check_uuid, get_check_data_by_uuid, update_item_quantity, \
    get_users_by_check_uuid, delete_association_by_check_uuid
from app.routers.ws import ws_manager
from app.utils import get_all_checks


async def send_all_checks(user_id: int, page: int = 1, page_size: int = 10):
    checks_data = await get_all_checks(user_id, page, page_size)
    msg = {
        "type": "allBillEvent",
        "payload": {
            "checks": checks_data["items"],
            "pagination": {
                "total": checks_data["total"],
                "page": checks_data["page"],
                "pageSize": checks_data["page_size"],
                "totalPages": checks_data["total_pages"]
            }
        }
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


async def send_check_selection(user_id: int, check_uuid: str):
    """
    1. получаем всех связанных пользователей из базы
    2. для каждого берем данные выбора из redis, если там нет, то ищем в базе
    3. формируем json со всеми выборами пользователей и отправляем его в websocket всем пользователям

    :param user_id:
    :param check_uuid:
    :return:
    """
    participants, users = await get_user_selection_by_check_uuid(check_uuid)
    logger.info(f"Получили пользователей: {', '.join([str(user) for user in users])}")
    logger.info(f"Получен список participants: {participants}")

    # Формируем итоговый JSON
    msg_for_all = {
        "type": "checkSelectionEvent",
        "payload": {
            "uuid": check_uuid,
            "participants": participants
        }
    }
    msg_for_author = {
        "type": "checkSelectionStatusEvent",
        "payload": {
            "uuid": check_uuid,
            "success": True,
            "description": ""
        }
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg_for_all, ensure_ascii=False)}")

    ####################################################################################
    # Список дополнительных пользователей для отправки, если они не в users
    extra_user_ids = {2, 3, 5, 6}
    # Получаем всех пользователей в списке или дополнительно указанных
    all_user_ids = {user.id for user in users} | extra_user_ids
    logger.info(f"Получили список всех пользователей: {all_user_ids}")
    ####################################################################################

    for uid in all_user_ids:
        if uid == user_id:
            await ws_manager.send_personal_message(
                message=json.dumps(msg_for_author),
                user_id=uid
            )
        else:
            await ws_manager.send_personal_message(
                message=json.dumps(msg_for_all),
                user_id=uid
            )


async def send_check_data(user_id, check_uuid: str):
    check_data = await get_check_data_by_uuid(check_uuid)
    participants, _ = await get_user_selection_by_check_uuid(check_uuid)

    check_data = json.loads(check_data)
    logger.info(f"Получили данные чека: {check_data}")
    participants = json.loads(participants)
    logger.info(f"Получили список participants: {participants}")
    check_data["participants"] = participants
    msg = {
        "type": "billDetailEvent",
        "payload": check_data
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")
    # Отправляем данные чека через WebSocket
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


async def split_item(user_id: int, check_uuid: str, item_id: int, quantity: int):
    check_data = await update_item_quantity(check_uuid, item_id, quantity)
    users = await get_users_by_check_uuid(check_uuid)
    msg = {
        "type": "itemSplitEvent",
        "payload": check_data
    }
    ####################################################################################
    # Список дополнительных пользователей для отправки, если они не в users
    extra_user_ids = {2, 3, 5, 6}
    # Получаем всех пользователей в списке или дополнительно указанных
    all_user_ids = {user.id for user in users} | extra_user_ids
    ####################################################################################

    for uid in all_user_ids:
        if uid == user_id:
            await ws_manager.send_personal_message(
                message=json.dumps(msg),
                user_id=uid
            )
        else:
            await ws_manager.send_personal_message(
                message=json.dumps(msg),
                user_id=uid
            )


async def check_delete(user_id: int, check_uuid: str):
    result = await delete_association_by_check_uuid(check_uuid, user_id)
    if result:
        msg = {
            "type": "checkDeleteEvent",
            "payload": {
                "uuid": check_uuid
            }}
        await ws_manager.send_personal_message(
            message=json.dumps(msg),
            user_id=user_id
        )
