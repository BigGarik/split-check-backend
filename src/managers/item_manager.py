import json
import logging
from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.type_events import Events
from src.repositories.item import (
    add_item_to_check,
    remove_item_from_check,
    edit_item_in_check, update_item_quantity
)
from src.repositories.user import get_users_by_check_uuid
from src.schemas import AddItemRequest, EditItemRequest
from src.utils.notifications import create_event_message, create_event_status_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


class ItemService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    async def _send_ws_message(user_id: int, message: Dict[str, Any]) -> None:
        await ws_manager.send_personal_message(
            message=json.dumps(message),
            user_id=user_id
        )

    async def add_item(self, user_id: int, check_uuid: str, item_data: dict):
        try:
            # Преобразуем данные запроса в объект Pydantic
            item_request = AddItemRequest(**item_data)
            new_item = await add_item_to_check(self.session, check_uuid, item_request)

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

            users = await get_users_by_check_uuid(self.session, check_uuid)
            for user in users:
                if user.id == user_id:
                    await self._send_ws_message(user_id, msg_for_all)
                else:
                    await self._send_ws_message(user.id, msg_for_all)

        except Exception as e:
            logger.error(f"Error adding item to check: {str(e)}", extra={"current_user_id": user_id})
            error_message = create_event_status_message(
                message_type=Events.ITEM_ADD_EVENT_STATUS,
                status="error",
                message=str(e)
            )
            await self._send_ws_message(user_id, error_message)
            raise e

    async def delete_item(self, user_id: int, check_uuid: str, item_id: int):
        try:
            await remove_item_from_check(self.session, check_uuid, item_id)

            msg_for_all = create_event_message(
                message_type=Events.ITEM_REMOVE_EVENT,
                payload={"uuid": check_uuid, "itemId": item_id}
            )
            msg_for_author = create_event_status_message(
                message_type=Events.ITEM_REMOVE_EVENT_STATUS,
                status="success",
                message="Item successfully removed from check"
            )

            users = await get_users_by_check_uuid(self.session, check_uuid)
            for user in users:
                if user.id == user_id:
                    await self._send_ws_message(user_id, msg_for_all)
                else:
                    await self._send_ws_message(user.id, msg_for_all)

        except Exception as e:
            logger.error(f"Error removing item from check: {str(e)}", extra={"current_user_id": user_id})
            error_message = create_event_status_message(
                message_type=Events.ITEM_REMOVE_EVENT_STATUS,
                status="error",
                message=str(e)
            )
            await self._send_ws_message(user_id, error_message)
            raise e

    async def edit_item(self, user_id: int, check_uuid: str, item_data: dict):
        try:
            item_request = EditItemRequest(**item_data)
            updated_data = await edit_item_in_check(self.session, check_uuid, item_request)

            msg_for_all = create_event_message(
                message_type=Events.ITEM_EDIT_EVENT,
                payload={"uuid": check_uuid, "new_check_data": updated_data}
            )
            msg_for_author = create_event_status_message(
                message_type=Events.ITEM_EDIT_EVENT_STATUS,
                status="success",
                message="Item successfully edited in check"
            )

            users = await get_users_by_check_uuid(self.session, check_uuid)
            for user in users:
                if user.id == user_id:
                    await self._send_ws_message(user_id, msg_for_all)
                else:
                    await self._send_ws_message(user.id, msg_for_all)

        except Exception as e:
            logger.error(f"Error editing item in check: {str(e)}", extra={"current_user_id": user_id})
            error_message = create_event_status_message(
                message_type=Events.ITEM_EDIT_EVENT_STATUS,
                status="error",
                message=str(e)
            )
            await self._send_ws_message(user_id, error_message)
            raise e

    async def split_item(self, user_id: int, check_uuid: str, item_data: dict):
        try:
            item_id = item_data["item_id"]
            quantity = item_data["quantity"]

            await update_item_quantity(self.session, check_uuid, item_id, quantity)
            users = await get_users_by_check_uuid(self.session, check_uuid)

            msg_for_all = create_event_message(
                message_type=Events.ITEM_SPLIT_EVENT,
                payload={"check_uuid": check_uuid, "item_id": item_id, "quantity": quantity}
            )

            for user in users:
                if user.id == user_id:
                    status_message = create_event_status_message(
                        message_type=Events.ITEM_SPLIT_EVENT_STATUS,
                        status="success"
                    )
                    await self._send_ws_message(user_id, status_message)
                else:
                    await self._send_ws_message(user.id, msg_for_all)

        except Exception as e:
            logger.error(f"Error splitting item: {str(e)}")
            error_message = create_event_status_message(
                message_type=Events.ITEM_SPLIT_EVENT_STATUS,
                status="error",
                message=str(e)
            )
            await self._send_ws_message(user_id, error_message)
            raise e
