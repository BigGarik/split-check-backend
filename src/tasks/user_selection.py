import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.type_events import Events
from src.repositories.user import get_users_by_check_uuid
from src.repositories.user_selection import add_or_update_user_selection
from src.utils.notifications import create_event_message, create_event_status_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


# refac
async def user_selection_task(user_id: int,
                              check_uuid: str,
                              selection_data: dict,
                              session: AsyncSession):
    """
    Обновляет выбор пользователя и отправляет обновленную информацию всем связанным пользователям.

    :param session:
    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные выбора для сохранения
    """

    logger.debug(f"user_selection_task: {user_id}, {check_uuid}, {selection_data}")
    try:
        # Обновляем или добавляем выбор пользователя
        await add_or_update_user_selection(session, user_id=user_id, check_uuid=check_uuid, selection_data=selection_data)

        # Получаем участников и пользователей, связанных с чеком
        users = await get_users_by_check_uuid(session, check_uuid)

        selections = {
            "user_id": user_id,
            "selected_items": selection_data['selected_items']
        }

        logger.info(f"selection_data: {selections}")

        all_user_ids = {user.id for user in users}

        # Формируем сообщения
        msg_for_all = create_event_message(
            message_type=Events.CHECK_SELECTION_EVENT,
            payload={"uuid": check_uuid, "participants": [selections]},
        )
        msg_for_author = create_event_status_message(
            message_type=Events.CHECK_SELECTION_EVENT_STATUS,
            status="success"
        )

        # Отправка сообщений всем пользователям
        for uid in all_user_ids:
            msg = msg_for_author if uid == user_id else msg_for_all
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg),
                    user_id=uid)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")

    except Exception as e:
        # Логируем ошибку и отправляем инициатору сообщение об ошибке
        logger.error(f"Ошибка при выполнении задачи выбора пользователя: {str(e)}")

        error_message = create_event_status_message(message_type=Events.CHECK_SELECTION_EVENT_STATUS,
                                                    status="error",
                                                    message="Ошибка при обработке")
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )











