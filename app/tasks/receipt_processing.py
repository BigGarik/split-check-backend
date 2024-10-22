import json

from loguru import logger

from app.crud import get_users_by_check, get_user_selection_by_user
from app.redis import redis_client
from app.routers.ws import ws_manager
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


async def send_check_selection(check_uuid: str):
    """
    1. получаем всех связанных пользователей из базы
    2. для каждого берем данные выбора из redis, если там нет, то ищем в базе
    3. формируем json со всеми выборами пользователей и отправляем его в websocket всем пользователям

    :param check_uuid:
    :return:
    """
    users = await get_users_by_check(check_uuid)
    logger.info(f"Получили пользователей: {users}")
    participants = []
    for user in users:
        redis_key = f"user_selection:{user.id}:{check_uuid}"
        logger.info(f"Получили redis_key: {redis_key}")
        user_selection = await redis_client.get(redis_key)
        logger.info(f"Получили user_selection из redis: {user_selection}")
        if not user_selection:
            user_selection = await get_user_selection_by_user(user.id)
            logger.info(f"Получили user_selection из базы: {user_selection}")
            # Преобразуем строку JSON в словарь Python
        if user_selection:
            selection_data = json.loads(user_selection)
            logger.info(f"Получили selection_data: {selection_data}")

            # Создаем структуру для каждого участника
            participant = {
                "userid": user.id,
                "selectedItems": []
            }

            # Добавляем выбранные предметы пользователя
            for item in selection_data.get('selected_items', []):
                selected_item = {
                    "itemId": item['item_id'],
                    "quantity": item['quantity']
                }
                participant["selectedItems"].append(selected_item)

            participants.append(participant)

    # Формируем итоговый JSON
    msg = {
        "type": "checkSelectionEvent",
        "payload": {
            "uuid": check_uuid,
            "participants": participants
        }
    }
    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")

    for user in users:
        await ws_manager.send_personal_message(
            message=json.dumps(msg),
            user_id=user.id
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
