import json

from loguru import logger

from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.repositories.check import update_item_quantity
from src.repositories.item import add_item_to_check, remove_item_from_check, edit_item_in_check
from src.repositories.user import get_users_by_check_uuid
from src.schemas import AddItemRequest, DeleteItemRequest, EditItemRequest
from src.utils.notifications import create_event_message, create_event_status_message


async def add_item_task(user_id: int, item_data: dict):
    try:
        # Преобразуем данные запроса в объект Pydantic
        item_request = AddItemRequest(**item_data)
        logger.debug(item_request)

        # Вызываем функцию добавления позиции в чек
        new_item = await add_item_to_check(item_request)
        logger.debug(new_item)

        # Формируем сообщение для отправки всем пользователям, связанным с чеком
        msg_for_all = {
            "type": settings.Events.ITEM_ADD_EVENT,
            "payload": {
                "uuid": item_request.uuid,
                "item": {
                    "id": new_item["id"],
                    "name": new_item["name"],
                    "quantity": new_item["quantity"],
                    "price": new_item["price"]
                }
            }
        }

        # Получаем всех пользователей, связанных с чеком
        users = await get_users_by_check_uuid(item_request.uuid)

        # Отправляем сообщение инициатору об успешном добавлении
        msg_for_author = {
            "type": settings.Events.ITEM_ADD_EVENT_STATUS,
            "status": "success",
            "message": "Item successfully added to check"
        }

        for user in users:
            if user.id == user_id:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_author),
                    user_id=user_id
                )
            else:
                # Отправляем уведомление всем связанным пользователям
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_all),
                    user_id=user.id
                )

    except Exception as e:
        logger.error(f"Error adding item to check: {str(e)}")

        # Отправляем сообщение инициатору об ошибке
        error_message = {
            "type": settings.Events.ITEM_ADD_EVENT_STATUS,
            "status": "error",
            "message": str(e)
        }
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
        raise e


async def delete_item_task(user_id: int, item_data: dict):
    try:
        # Преобразуем данные запроса в объект Pydantic
        item_request = DeleteItemRequest(**item_data)
        # Вызываем функцию удаления позиции из чека
        removed_item = await remove_item_from_check(item_request.uuid, item_request.id)

        # Формируем сообщение для отправки всем пользователям, связанным с чеком
        msg_for_all = {
            "type": settings.Events.ITEM_REMOVE_EVENT,
            "payload": {
                "uuid": item_request.uuid,
                "itemId": item_request.id
            }
        }

        # Получаем всех пользователей, связанных с чеком
        users = await get_users_by_check_uuid(item_request.uuid)

        # Отправляем сообщение инициатору об успешном удалении
        msg_for_author = {
            "type": settings.Events.ITEM_REMOVE_EVENT_STATUS,
            "status": "success",
            "message": "Item successfully removed from check"
        }

        for user in users:
            if user.id == user_id:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_author),
                    user_id=user_id
                )
            else:
                # Отправляем уведомление всем связанным пользователям
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_all),
                    user_id=user.id
                )

    except Exception as e:
        logger.error(f"Error removing item from check: {str(e)}")
        # Отправляем сообщение инициатору об ошибке
        error_message = {
            "type": settings.Events.ITEM_REMOVE_EVENT_STATUS,
            "status": "error",
            "message": str(e)
        }
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
        raise e


async def edit_item_task(user_id: int, item_data: dict):
    try:
        # Преобразуем данные запроса в объект Pydantic
        item_request = EditItemRequest(**item_data)
        logger.debug(item_request)
        # Вызываем функцию редактирования позиции из чека
        new_check_data = await edit_item_in_check(item_request)

        # Формируем сообщение для отправки всем пользователям, связанным с чеком
        msg_for_all = {
            "type": settings.Events.ITEM_EDIT_EVENT,
            "payload": {
                "uuid": item_request.uuid,
                "new_check_data": new_check_data
            }
        }

        # Получаем всех пользователей, связанных с чеком
        users = await get_users_by_check_uuid(item_request.uuid)

        # Отправляем сообщение инициатору об успешном удалении
        msg_for_author = {
            "type": settings.Events.ITEM_EDIT_EVENT_STATUS,
            "status": "success",
            "message": "Item successfully edited in check"
        }

        for user in users:
            if user.id == user_id:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_author),
                    user_id=user_id
                )
            else:
                # Отправляем уведомление всем связанным пользователям
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_all),
                    user_id=user.id
                )

    except Exception as e:
        logger.error(f"Error editing item: {str(e)}")
        error_message = {
            "type": settings.Events.ITEM_EDIT_EVENT_STATUS,
            "status": "error",
            "message": str(e)
        }
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
        raise e


async def split_item_task(user_id: int, check_uuid: str, item_id: int, quantity: int):
    try:
        # Обновляем количество в базе данных
        await update_item_quantity(check_uuid, item_id, quantity)
        users = await get_users_by_check_uuid(check_uuid)

        # Подготовка данных для связанных пользователей
        msg_for_related_users = create_event_message(message_type=settings.Events.ITEM_SPLIT_EVENT,
                                                     payload={
                                                         "check_uuid": check_uuid,
                                                         "item_id": item_id,
                                                         "quantity": quantity
                                                     })
        #############################################################################
        # Список дополнительных пользователей для оповещения
        extra_user_ids = {2, 3, 5, 6}
        all_user_ids = {user.id for user in users} | extra_user_ids
        #############################################################################

        # Отправка подтверждения инициатору и данных связанным пользователям
        for uid in all_user_ids:
            if uid == user_id:
                status_message = create_event_status_message(message_type=settings.Events.ITEM_SPLIT_EVENT_STATUS,
                                                             status="success")
                await ws_manager.send_personal_message(
                    message=json.dumps(status_message),
                    user_id=uid
                )
            else:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_related_users),
                    user_id=uid
                )

    except Exception as e:
        logger.error(f"Ошибка при разделении позиции: {str(e)}")
        # Обработка ошибки для инициатора
        error_message = create_event_status_message(message_type=settings.Events.ITEM_SPLIT_EVENT_STATUS,
                                                    status="error",
                                                    message=str(e))
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
