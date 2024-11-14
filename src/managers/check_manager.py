import json
from datetime import datetime
from typing import Dict, Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException

from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.redis import redis_client
from src.repositories.check import (
    get_all_checks,
    add_check_to_database,
    delete_association_by_check_uuid,
    get_check_by_uuid,
    update_check_data_to_database
)
from src.repositories.user_selection import get_user_selection_by_check_uuid
from src.services.user import join_user_to_check
from src.utils.notifications import create_event_message, create_event_status_message


class CheckManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    async def _send_ws_message(user_id: int, message: Dict[str, Any]) -> None:
        await ws_manager.send_personal_message(
            message=json.dumps(message),
            user_id=user_id
        )

    async def _handle_error(self, user_id: int, event_type: str, error: Exception) -> None:
        logger.error(f"Error in {event_type}: {str(error)}")
        error_message = create_event_status_message(
            message_type=event_type,
            status="error",
            message=str(error)
        )
        await self._send_ws_message(user_id, error_message)

    @staticmethod
    async def get_check_data_by_uuid(check_uuid: str) -> Dict[str, Any]:
        redis_key = f"check_uuid:{check_uuid}"

        # Попытка получить данные из Redis
        cached_data = await redis_client.get(redis_key)
        if cached_data:
            logger.debug(f"Получены данные чека из Redis: {check_uuid}")
            return json.loads(cached_data)

        # Если нет в Redis, ищем в базе данных
        check = await get_check_by_uuid(check_uuid)
        if not check:
            logger.warning(f"Чек не найден: {check_uuid}")
            raise HTTPException(status_code=404, detail="Check not found")

        # Кэширование в Redis
        await redis_client.set(
            redis_key,
            json.dumps(check.check_data),
            expire=settings.redis_expiration
        )

        logger.debug(f"Данные чека получены из БД: {check_uuid}")
        return check.check_data

    @staticmethod
    async def update_check_data(check_uuid: str, check_data: dict) -> dict:

        await update_check_data_to_database(check_data)

        # Обновляем кэш Redis
        redis_key = f"check_uuid:{check_uuid}"
        await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
        return check_data

    async def send_check_data(self, user_id: int, check_uuid: str) -> None:
        check_data = await self.get_check_data_by_uuid(check_uuid)
        participants, _ = await get_user_selection_by_check_uuid(check_uuid)

        check_data["participants"] = json.loads(participants)
        msg = create_event_message(settings.Events.BILL_DETAIL_EVENT, check_data)

        await self._send_ws_message(user_id, msg)

    async def send_all_checks(self, user_id: int, page: int = 1, page_size: int = 10) -> None:
        checks_data = await get_all_checks(self.session, user_id, page, page_size)
        msg = create_event_message(
            message_type=settings.Events.ALL_BILL_EVENT,
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
        await self._send_ws_message(user_id, msg)

    async def create_empty(self, user_id: int, check_uuid: str) -> None:
        check_data = {
            "restaurant": "",
            "table_number": "",
            "order_number": "",
            "date": datetime.now().strftime("%d.%m.%Y"),
            "time": datetime.now().strftime("%H:%M"),
            "waiter": "",
            "items": [],
            "subtotal": 0,
            "service_charge": {"name": "", "amount": 0},
            "vat": {"rate": 0, "amount": 0},
            "total": 0
        }
        await add_check_to_database(check_uuid, user_id, check_data)

        # Кэширование в Redis
        await redis_client.set(
            f"check_uuid:{check_uuid}",
            json.dumps(check_data),
            expire=settings.redis_expiration
        )

        msg = create_event_message(
            message_type=settings.Events.CHECK_ADD_EVENT,
            payload={"uuid": check_uuid}
        )
        await self._send_ws_message(user_id, msg)

    async def join_check(self, user_id: int, check_uuid: str) -> None:
        try:
            await join_user_to_check(user_id, check_uuid)
            status_message = create_event_status_message(
                message_type=settings.Events.JOIN_BILL_EVENT_STATUS,
                status="success"
            )
            await self._send_ws_message(user_id, status_message)
        except Exception as e:
            await self._handle_error(user_id, settings.Events.JOIN_BILL_EVENT_STATUS, e)

    async def delete_check(self, user_id: int, check_uuid: str) -> None:
        try:
            await delete_association_by_check_uuid(check_uuid, user_id)
            status_message = create_event_status_message(
                message_type=settings.Events.CHECK_DELETE_EVENT_STATUS,
                status="success"
            )
            await self._send_ws_message(user_id, status_message)
        except Exception as e:
            await self._handle_error(user_id, settings.Events.CHECK_DELETE_EVENT_STATUS, e)


async def get_check_manager(session: AsyncSession) -> CheckManager:
    return CheckManager(session)
