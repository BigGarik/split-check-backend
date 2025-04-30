import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.type_events import Events
from src.repositories.check import get_check_data_from_database
from src.repositories.item import update_item_quantity, add_item_to_check
from src.repositories.user import get_users_by_check_uuid
from src.utils.notifications import create_event_message, create_event_status_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


# refac
async def add_item_task(user_id: int, check_uuid: str, item_data: dict, session: AsyncSession):
    try:

        users = await get_users_by_check_uuid(session, check_uuid)
        # Преобразуем данные запроса в объект Pydantic
        # item_request = AddItemRequest(**item_data)
        new_item = await add_item_to_check(session, check_uuid, item_data)

        # Получаем данные чека и кешируем данные в редис
        await get_check_data_from_database(session, check_uuid)

        # Формируем сообщение для отправки
        msg_for_all = create_event_message(
            message_type=Events.ITEM_ADD_EVENT,
            payload={"uuid": check_uuid, "item": new_item}
        )
        msg_for_author = create_event_status_message(
            message_type=Events.ITEM_ADD_EVENT_STATUS,
            status="success",
            message="Item successfully added to check"
        )

        all_user_ids = {user.id for user in users}

        # Отправка сообщений всем пользователям
        for uid in all_user_ids:
            msg = msg_for_author if uid == user_id else msg_for_all
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg),
                    user_id=uid
                )
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}",
                             extra={"current_user_id": user_id})

    except Exception as e:
        logger.error(f"Error in {Events.ITEM_ADD_EVENT}: {str(e)}",
                     extra={"current_user_id": user_id})

        error_message = create_event_status_message(
            message_type=Events.ITEM_ADD_EVENT,
            status="error",
            message=str(e)
        )
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )


async def delete_item_task(user_id: int,
                           check_uuid: str,
                           item_id: int,
                           session: AsyncSession):
    pass
    # await check_manager.delete_item(user_id, check_uuid, item_id)


async def edit_item_task(user_id: int,
                         check_uuid: str,
                         item_data: dict,
                         session: AsyncSession):
    pass
    # await check_manager.edit_item(user_id, check_uuid, item_data)


# refac
async def split_item_task(user_id: int, check_uuid: str, item_data: dict, session: AsyncSession):
    try:
        item_id = item_data["item_id"]
        quantity = item_data["quantity"]

        await update_item_quantity(session, check_uuid, item_id, quantity)
        # Получаем данные чека и кешируем данные в редис
        await get_check_data_from_database(session, check_uuid)
        users = await get_users_by_check_uuid(session, check_uuid)

        msg_for_author = create_event_status_message(
            message_type=Events.ITEM_SPLIT_EVENT_STATUS,
            status="success",
            message="Item successfully edited in check"
        )

        msg_for_all = create_event_message(
            message_type=Events.ITEM_SPLIT_EVENT,
            payload={"check_uuid": check_uuid, "item_id": item_id, "quantity": quantity}
        )

        all_user_ids = {user.id for user in users}

        # Отправка сообщений всем пользователям
        for uid in all_user_ids:
            msg = msg_for_author if uid == user_id else msg_for_all
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg),
                    user_id=uid
                )
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}",
                               extra={"current_user_id": user_id})

    except Exception as e:
        logger.error(f"Error in {Events.ITEM_SPLIT_EVENT}: {str(e)}",
                     extra={"current_user_id": user_id})

        error_message = create_event_status_message(
            message_type=Events.ITEM_SPLIT_EVENT,
            status="error",
            message=str(e)
        )
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )
