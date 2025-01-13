import json
from datetime import datetime
from typing import Dict, Any

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException

from src.api.v1.endpoints.websockets import ws_manager
from src.config.settings import settings
from src.managers.item_manager import ItemService
from src.redis import redis_client
from src.repositories.check import (
    get_all_checks,
    add_check_to_database,
    delete_association_by_check_uuid,
    get_check_by_uuid,
    update_check_data_to_database, get_main_page_checks, is_check_author, edit_check_name_to_database,
    edit_check_status_to_database
)
from src.repositories.user import get_users_by_check_uuid, get_user_by_id
from src.repositories.user_selection import get_user_selection_by_check_uuid, add_or_update_user_selection
from src.services.user import join_user_to_check
from src.utils.notifications import create_event_message, create_event_status_message


class CheckManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.item_service = ItemService(session)

    # Используем метод из ItemService
    async def add_item(self, user_id: int, check_uuid: str, item_data: dict):
        await self.item_service.add_item(user_id, check_uuid, item_data)

    async def delete_item(self, user_id: int, check_uuid: str, item_id: int):
        await self.item_service.delete_item(user_id, check_uuid, item_id)

    async def edit_item(self, user_id: int, check_uuid: str, item_data: dict):
        await self.item_service.edit_item(user_id, check_uuid, item_data)

    async def split_item(self, user_id: int, check_uuid: str, item_data: dict):
        await self.item_service.split_item(user_id, check_uuid, item_data)

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

    async def add_check(self, user_id: int, check_uuid: str, check_data: dict) -> None:

        await add_check_to_database(self.session, check_uuid, user_id, check_data)

        # Сохранение результатов в Redis
        redis_key = f"check_uuid:{check_uuid}"
        await redis_client.set(redis_key,
                               json.dumps(check_data),
                               expire=settings.redis_expiration)

        msg = create_event_message(
            message_type=settings.Events.IMAGE_RECOGNITION_EVENT,
            payload={"uuid": check_uuid}
        )
        await self._send_ws_message(user_id, msg)

    async def get_check_data_by_uuid(self, check_uuid: str) -> Dict[str, Any]:
        redis_key = f"check_uuid:{check_uuid}"

        # Попытка получить данные из Redis
        cached_data = await redis_client.get(redis_key)
        if cached_data:
            logger.debug(f"Получены данные чека из Redis: {check_uuid}")
            return json.loads(cached_data)

        # Если нет в Redis, ищем в базе данных
        check = await get_check_by_uuid(self.session, check_uuid)
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

    async def update_check_data(self, check_uuid: str, check_data: dict) -> dict:

        await update_check_data_to_database(self.session, check_uuid, check_data)

        # Обновляем кэш Redis
        redis_key = f"check_uuid:{check_uuid}"
        await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
        return check_data

    async def edit_check_name(self, user_id: int, check_uuid: str, check_name: str):
        new_name_status = await edit_check_name_to_database(self.session, user_id, check_uuid, check_name)
        users = await get_users_by_check_uuid(self.session, check_uuid)
        if new_name_status == "Check name updated successfully.":
            msg_for_author = create_event_status_message(
                message_type=settings.Events.CHECK_NAME_EVENT_STATUS,
                status="success"
            )

            msg_for_all = create_event_message(
                message_type=settings.Events.CHECK_NAME_EVENT,
                payload={"check_name": check_name},
            )

            all_user_ids = {user.id for user in users}
            logger.debug(f"Все пользователи для отправки: {all_user_ids}")

            # Отправка сообщений всем пользователям
            for uid in all_user_ids:
                msg = msg_for_author if uid == user_id else msg_for_all
                try:
                    await self._send_ws_message(uid, msg)
                except Exception as e:
                    logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")

    async def edit_check_status(self, user_id: int, check_uuid: str, check_status: str):
        status = await edit_check_status_to_database(self.session, user_id, check_uuid, check_status)
        users = await get_users_by_check_uuid(self.session, check_uuid)
        if status == "Check status updated successfully.":
            msg_for_author = create_event_status_message(
                message_type=settings.Events.CHECK_STATUS_EVENT_STATUS,
                status="success"
            )

            msg_for_all = create_event_message(
                message_type=settings.Events.CHECK_STATUS_EVENT,
                payload={"check_status": check_status},
            )

            all_user_ids = {user.id for user in users}
            logger.debug(f"Все пользователи для отправки: {all_user_ids}")

            # Отправка сообщений всем пользователям
            for uid in all_user_ids:
                msg = msg_for_author if uid == user_id else msg_for_all
                try:
                    await self._send_ws_message(uid, msg)
                except Exception as e:
                    logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")


    async def send_check_data(self, user_id: int, check_uuid: str) -> None:
        check_data = await self.get_check_data_by_uuid(check_uuid)
        participants, user_selections, _ = await get_user_selection_by_check_uuid(self.session, check_uuid)

        check_data["participants"] = json.loads(participants)
        check_data["user_selections"] = json.loads(user_selections)
        check = await get_check_by_uuid(self.session, check_uuid)
        check_data["name"] = check.name
        check_data["uuid"] = check_uuid
        check_data["author_id"] = check.author_id
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

    async def send_main_page_checks(self, user_id: int) -> None:
        checks_data = await get_main_page_checks(self.session, user_id)
        msg = create_event_message(
            message_type=settings.Events.MAIN_PAGE_EVENT,
            payload={
                "checks": checks_data["items"],
                "total_open": checks_data["total_open"],
                "total_closed": checks_data["total_closed"],
            }
        )
        logger.debug(msg)
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
        await add_check_to_database(self.session, check_uuid, user_id, check_data)

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
            joined_user = await get_user_by_id(self.session, user_id)
            users = await get_users_by_check_uuid(self.session, check_uuid)

            msg_for_author = create_event_status_message(
                message_type=settings.Events.JOIN_BILL_EVENT_STATUS,
                status="success"
            )

            msg_for_all = create_event_message(
                message_type=settings.Events.USER_JOIN_EVENT,
                payload={"user_id": joined_user.id,
                         "nickname": joined_user.profile.nickname,
                         "avatar_url": joined_user.profile.avatar_url,
                         },
            )

            all_user_ids = {user.id for user in users}
            logger.debug(f"Все пользователи для отправки: {all_user_ids}")

            # Отправка сообщений всем пользователям
            for uid in all_user_ids:
                msg = msg_for_author if uid == user_id else msg_for_all
                try:
                    await self._send_ws_message(uid, msg)
                except Exception as e:
                    logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")

        except Exception as e:
            await self._handle_error(user_id, settings.Events.JOIN_BILL_EVENT_STATUS, e)

    async def delete_check(self, user_id: int, check_uuid: str) -> None:
        try:
            await delete_association_by_check_uuid(self.session, check_uuid, user_id)
            status_message = create_event_status_message(
                message_type=settings.Events.CHECK_DELETE_EVENT_STATUS,
                status="success"
            )
            await self._send_ws_message(user_id, status_message)
        except Exception as e:
            await self._handle_error(user_id, settings.Events.CHECK_DELETE_EVENT_STATUS, e)

    async def handle_user_selection(self, user_id: int, check_uuid: str, selection_data: dict) -> None:
        """
        Обновляет выбор пользователя и отправляет обновленную информацию всем связанным пользователям.

        Args:
            user_id: Идентификатор пользователя
            check_uuid: UUID чека
            selection_data: Данные выбора для сохранения
        """
        logger.debug(f"handle_user_selection: {user_id}, {check_uuid}, {selection_data}")
        try:
            # Обновляем или добавляем выбор пользователя
            await add_or_update_user_selection(self.session,
                                               user_id=user_id,
                                               check_uuid=check_uuid,
                                               selection_data=selection_data)

            # Получаем участников и пользователей, связанных с чеком
            users = await get_users_by_check_uuid(self.session, check_uuid)
            # participants, users = await get_user_selection_by_check_uuid(self.session, check_uuid)

            selections = {
                "user_id": user_id,
                "selected_items": selection_data['selected_items']
            }
            logger.info(f"selection_data: {selections}")

            # Формируем сообщения
            msg_for_all = create_event_message(
                message_type=settings.Events.CHECK_SELECTION_EVENT,
                payload={"uuid": check_uuid, "participants": [selections]},
            )
            msg_for_author = create_event_status_message(
                message_type=settings.Events.CHECK_SELECTION_EVENT_STATUS,
                status="success"
            )

            all_user_ids = {user.id for user in users}
            logger.debug(f"Все пользователи для отправки: {all_user_ids}")

            # Отправка сообщений всем пользователям
            for uid in all_user_ids:
                msg = msg_for_author if uid == user_id else msg_for_all
                try:
                    await self._send_ws_message(uid, msg)
                except Exception as e:
                    logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")

        except Exception as e:
            await self._handle_error(
                user_id,
                settings.Events.CHECK_SELECTION_EVENT_STATUS,
                e
            )

    async def user_delete_from_check(self, session: AsyncSession, check_uuid: str, user_id_for_delete: int,
                                     current_user_id: int) -> None:
        """
        Удаляет ассоциацию пользователя с чеком. Только автор чека может выполнить это действие.

        Args:
            session (AsyncSession): Асинхронная сессия SQLAlchemy
            check_uuid (str): UUID чека
            user_id_for_delete (int): ID пользователя, которого нужно удалить из чека
            current_user_id (int): ID текущего пользователя (автора)

        Returns:
            bool: True если удаление успешно, False если текущий пользователь не автор

        Raises:
            SQLAlchemyError: При ошибках работы с базой данных
        """
        try:
            # Проверяем права автора
            if not await is_check_author(self.session, current_user_id, check_uuid):
                logger.warning(
                    f"User {current_user_id} attempted to delete user {user_id_for_delete} "
                    f"from check {check_uuid} without author rights"
                )
            # Удаляем ассоциацию пользователя с чеком
            await delete_association_by_check_uuid(self.session, check_uuid, user_id_for_delete)

            status_message = create_event_status_message(
                message_type=settings.Events.USER_DELETE_FROM_CHECK_EVENT_STATUS,
                status="success"
            )
            await self._send_ws_message(current_user_id, status_message)

            logger.debug(
                f"User {user_id_for_delete} was removed from check {check_uuid} "
                f"by author {current_user_id}"
            )

        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"Database error while deleting user from check: {e}")
            raise


async def get_check_manager(session: AsyncSession) -> CheckManager:
    return CheckManager(session)
