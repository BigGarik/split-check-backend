import json
import os

from fastapi import HTTPException
from loguru import logger
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import add_item_to_check, get_users_by_check_uuid, remove_item_from_check, edit_item_in_check
from app.database import with_db_session
from app.models import Check
from app.routers.ws import ws_manager
from app.schemas import AddItemRequest, DeliteItemRequest, EditItemRequest

load_dotenv()


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
            "type": "itemAddEvent",
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
            "type": "itemAddEventStatus",
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
            "type": "itemAddEventStatus",
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
        item_request = DeliteItemRequest(**item_data)
        # Вызываем функцию удаления позиции из чека
        removed_item = await remove_item_from_check(item_request.uuid, item_request.id)

        # Формируем сообщение для отправки всем пользователям, связанным с чеком
        msg_for_all = {
            "type": "itemRemoveEvent",
            "payload": {
                "uuid": item_request.uuid,
                "itemId": item_request.id
            }
        }

        # Получаем всех пользователей, связанных с чеком
        users = await get_users_by_check_uuid(item_request.uuid)

        # Отправляем сообщение инициатору об успешном удалении
        msg_for_author = {
            "type": "itemRemoveEventStatus",
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
            "type": "itemRemoveEventStatus",
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
            "type": "itemEditEvent",
            "payload": {
                "uuid": item_request.uuid,
                "new_check_data": new_check_data
            }
        }

        # Получаем всех пользователей, связанных с чеком
        users = await get_users_by_check_uuid(item_request.uuid)

        # Отправляем сообщение инициатору об успешном удалении
        msg_for_author = {
            "type": "itemEditEventStatus",
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
            "type": "itemEditEventStatus",
            "status": "error",
            "message": str(e)
        }
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
        raise e


if __name__ == '__main__':
    pass
