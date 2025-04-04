import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.managers.item_manager import ItemService
from src.redis import redis_client
from src.repositories.check import (
    get_all_checks,
    add_check_to_database,
    delete_association_by_check_uuid, get_main_page_checks, is_check_author, edit_check_name_to_database,
    edit_check_status_to_database, get_check_data_from_database
)
from src.repositories.item import get_items_by_check_uuid
from src.repositories.user import get_users_by_check_uuid, get_user_by_id
from src.repositories.user_selection import get_user_selection_by_check_uuid, add_or_update_user_selection
from src.services.user import join_user_to_check
from src.utils.check import to_float
from src.utils.exchange import get_exchange_rate
from src.utils.notifications import create_event_message, create_event_status_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


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
        logger.error(f"Error in {event_type}: {str(error)}", extra={"current_user_id": user_id})
        error_message = create_event_status_message(
            message_type=event_type,
            status="error",
            message=str(error)
        )
        await self._send_ws_message(user_id, error_message)

    async def add_check(self, user_id: int, check_uuid: str, recognized_json: dict) -> None:

        await add_check_to_database(self.session, check_uuid, user_id, recognized_json)
        cached_data = await self.get_check_data_by_uuid(check_uuid)
        logger.info(f"Чек {check_uuid} добавлен. cached_data: {cached_data}", extra={"current_user_id": user_id})

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
            logger.debug(f"Получены данные чека из Redis: {cached_data}")
            return json.loads(cached_data)

        check_data = await get_check_data_from_database(self.session, check_uuid)
        logger.debug(f"Данные чека получены из БД: {check_data}")

        return check_data

    # async def update_check_data(self, check_uuid: str, check_data: dict) -> dict:
    #
    #     await update_check_data_to_database(self.session, check_uuid, check_data)
    #
    #     # Обновляем кэш Redis
    #     redis_key = f"check_uuid:{check_uuid}"
    #     await redis_client.set(redis_key, json.dumps(check_data), expire=settings.redis_expiration)
    #     return check_data

    async def edit_check_name(self, user_id: int, check_uuid: str, check_name: str):
        new_name_status = await edit_check_name_to_database(self.session, user_id, check_uuid, check_name)

        if new_name_status == "Check name updated successfully.":
            users = await get_users_by_check_uuid(self.session, check_uuid)
            await self.get_check_data_by_uuid(check_uuid)
            msg_for_author = create_event_status_message(
                message_type=settings.Events.CHECK_NAME_EVENT_STATUS,
                status="success"
            )

            msg_for_all = create_event_message(
                message_type=settings.Events.CHECK_NAME_EVENT,
                payload={"check_uuid": check_uuid, "check_name": check_name},
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

        if status == "Check status updated successfully.":
            users = await get_users_by_check_uuid(self.session, check_uuid)
            await self.get_check_data_by_uuid(check_uuid)
            msg_for_author = create_event_status_message(
                message_type=settings.Events.CHECK_STATUS_EVENT_STATUS,
                status="success"
            )

            msg_for_all = create_event_message(
                message_type=settings.Events.CHECK_STATUS_EVENT,
                payload={"check_uuid": check_uuid, "check_status": check_status},
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
        msg = create_event_message(settings.Events.BILL_DETAIL_EVENT, check_data)

        await self._send_ws_message(user_id, msg)

    async def send_all_checks(self, user_id: int,
                              page: int,
                              page_size: int,
                              check_name: Optional[str] = None,
                              check_status: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> None:
        checks_data = await get_all_checks(self.session,
                                           user_id=user_id,
                                           page=page,
                                           page_size=page_size,
                                           check_name=check_name,
                                           check_status=check_status,
                                           start_date=start_date,
                                           end_date=end_date)
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
            "date": datetime.now().strftime("%d.%m.%Y"),
            "time": datetime.now().strftime("%H:%M"),
        }
        await add_check_to_database(self.session, check_uuid, user_id, check_data)
        await self.get_check_data_by_uuid(check_uuid)

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

    async def user_delete_from_check(self, # session: AsyncSession,
                                     check_uuid: str,
                                     user_id_for_delete: int,
                                     current_user_id: int)-> bool:
        """
        Удаляет ассоциацию пользователя с чеком. Только автор чека может выполнить это действие.

        Args:
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
                return False
            # Удаляем ассоциацию пользователя с чеком
            await delete_association_by_check_uuid(self.session, check_uuid, user_id_for_delete)

            msg_for_all = create_event_message(
                message_type=settings.Events.USER_DELETE_FROM_CHECK_EVENT,
                payload={"uuid": check_uuid, "user_id_for_delete ": user_id_for_delete}
            )

            msg_for_author = create_event_status_message(
                message_type=settings.Events.USER_DELETE_FROM_CHECK_EVENT_STATUS,
                status="success"
            )
            # Получаем участников и пользователей, связанных с чеком
            users = await get_users_by_check_uuid(self.session, check_uuid)

            all_user_ids = {user.id for user in users}

            # Отправка сообщений всем пользователям
            for uid in all_user_ids:
                msg = msg_for_author if uid == current_user_id else msg_for_all
                try:
                    await self._send_ws_message(uid, msg)
                except Exception as e:
                    logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}", extra={"current_user_id": current_user_id})

            logger.debug(
                f"User {user_id_for_delete} was removed from check {check_uuid} "
                f"by author {current_user_id}", extra={"current_user_id": current_user_id}
            )
            return True

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Database error while deleting user from check: {e}", extra={"current_user_id": current_user_id})
            raise

    async def convert_check_currency(self, check_uuid: str, target_currency: str) -> dict:
        """
        Конвертирует данные чека из его валюты в целевую валюту.

        Args:
            session: AsyncSession - сессия базы данных
            check_uuid: str - UUID чека
            target_currency: str - Целевая валюта (например, "USD", "EUR")

        Returns:
            dict: Данные чека с конвертированными суммами в целевой валюте

        Raises:
            Exception: Если чек не найден или произошла ошибка при конвертации
        """
        try:
            # Получаем данные чека из базы
            check_data = await get_check_data_from_database(self.session, check_uuid)

            # Валюта чека
            check_currency = check_data["currency"]
            if check_currency == target_currency:
                logger.info(f"Валюта чека {check_currency} совпадает с целевой валютой {target_currency}")
                return check_data  # Нет необходимости конвертировать, если валюты совпадают

            # Получаем курс обмена
            exchange_rate = await get_exchange_rate(check_currency, target_currency)
            if exchange_rate is None:
                raise Exception(f"Не удалось получить курс обмена между {check_currency} и {target_currency}")

            # Создаем копию данных чека для изменений
            converted_check_data = check_data.copy()

            # Конвертируем основные суммы
            converted_check_data["subtotal"] = converted_check_data["subtotal"] / exchange_rate
            converted_check_data["total"] = converted_check_data["total"] / exchange_rate

            # Конвертируем дополнительные суммы (service_charge, vat, discount), если они есть
            if converted_check_data["service_charge"]:
                converted_check_data["service_charge"]["amount"] = (
                    converted_check_data["service_charge"]["amount"] / exchange_rate
                    if converted_check_data["service_charge"]["amount"] is not None else None
                )

            if converted_check_data["vat"]:
                converted_check_data["vat"]["amount"] = (
                    converted_check_data["vat"]["amount"] / exchange_rate
                    if converted_check_data["vat"]["amount"] is not None else None
                )

            if converted_check_data["discount"]:
                converted_check_data["discount"]["amount"] = (
                    converted_check_data["discount"]["amount"] / exchange_rate
                    if converted_check_data["discount"]["amount"] is not None else None
                )

            # Конвертируем суммы для каждой позиции в чеке
            for item in converted_check_data["items"]:
                item["sum"] = item["sum"] / exchange_rate

            # Обновляем валюту чека
            converted_check_data["currency"] = target_currency

            print(converted_check_data)

            return converted_check_data

        except Exception as e:
            logger.error(f"Error while converting check currency: {e}")
            raise

async def get_check_manager(session: AsyncSession) -> CheckManager:
    return CheckManager(session)
