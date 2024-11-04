import json

from loguru import logger

from app.crud import get_user_selection_by_check_uuid, get_check_data_by_uuid, update_item_quantity, \
    get_users_by_check_uuid, delete_association_by_check_uuid, add_or_update_user_selection, get_all_checks, \
    join_user_to_check
from app.routers.ws import ws_manager
from app.schemas import CheckSelectionRequest
from app.utils import create_event_message, create_event_status_message


async def send_all_checks(user_id: int, page: int = 1, page_size: int = 10):

    checks_data = await get_all_checks(user_id, page, page_size)

    msg = create_event_message(message_type="allBillEvent",
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

    logger.info(f"Отправляем сообщение: {json.dumps(msg, ensure_ascii=False)}")

    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


async def user_selection_task(user_id: int, check_uuid: str, selection_data: dict):
    """
    Обновляет выбор пользователя и отправляет обновленную информацию всем связанным пользователям.

    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные выбора для сохранения
    """
    try:
        # Обновляем или добавляем выбор пользователя
        await add_or_update_user_selection(user_id=user_id, check_uuid=check_uuid, selection_data=selection_data)

        # Получаем участников и пользователей, связанных с чеком
        participants, users = await get_user_selection_by_check_uuid(check_uuid)
        logger.info(f"Участники: {participants}")
        logger.info(f"Пользователи: {', '.join([str(user) for user in users])}")

        # Формируем сообщения
        msg_for_all = create_event_message(message_type="checkSelectionEvent",
                                           payload={"uuid": check_uuid, "participants": participants},
                                           )
        msg_for_author = create_event_status_message("checkSelectionEventStatus", "success")

        # Получаем все user_id для рассылки сообщений
        extra_user_ids = {2, 3, 5, 6}
        all_user_ids = {user.id for user in users} | extra_user_ids
        logger.info(f"Все пользователи для отправки: {all_user_ids}")

        # Отправка сообщений всем пользователям
        for uid in all_user_ids:
            msg = msg_for_author if uid == user_id else msg_for_all
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg),
                    user_id=uid)
            except Exception as e:
                logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")

    except Exception as e:
        # Логируем ошибку и отправляем инициатору сообщение об ошибке
        logger.error(f"Ошибка при выполнении задачи выбора пользователя: {str(e)}")

        error_message = create_event_status_message("checkSelectionEventStatus", "error",
                                                    message="Ошибка при обработке")
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )


async def send_check_data(user_id, check_uuid: str):
    check_data = await get_check_data_by_uuid(check_uuid)
    participants, _ = await get_user_selection_by_check_uuid(check_uuid)

    check_data = json.loads(check_data)
    logger.info(f"Получили данные чека: {check_data}")
    participants = json.loads(participants)
    logger.info(f"Получили список participants: {participants}")
    check_data["participants"] = participants

    msg_check_data = create_event_message("billDetailEvent", payload=check_data)

    logger.info(f"Отправляем сообщение: {json.dumps(msg_check_data, ensure_ascii=False)}")

    # Отправляем данные чека через WebSocket
    await ws_manager.send_personal_message(
        message=json.dumps(msg_check_data),
        user_id=user_id
    )


async def split_item(user_id: int, check_uuid: str, item_id: int, quantity: int):
    try:
        # Обновляем количество в базе данных
        await update_item_quantity(check_uuid, item_id, quantity)
        users = await get_users_by_check_uuid(check_uuid)

        # Подготовка данных для связанных пользователей
        msg_for_related_users = create_event_message("itemSplitEvent",
                                                     {
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
                status_message = create_event_status_message("itemSplitEventStatus", "success")
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
        error_message = create_event_status_message("itemSplitEventStatus", "error", message=str(e))
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )


async def check_delete(user_id: int, check_uuid: str):
    try:
        await delete_association_by_check_uuid(check_uuid, user_id)
        status_message = create_event_status_message("checkDeleteEventStatus", "success")
        await ws_manager.send_personal_message(
            message=json.dumps(status_message),
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при разделении позиции: {str(e)}")
        # Обработка ошибки для инициатора
        error_message = create_event_status_message("checkDeleteEventStatus", "error", message=str(e))
        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )


async def join_check_task(user_id: int, check_uuid: str):
    try:
        await join_user_to_check(user_id, check_uuid)

        status_message = create_event_status_message("joinBillEventStatus", "success")

        await ws_manager.send_personal_message(
            message=json.dumps(status_message),
            user_id=user_id
        )
    except Exception as e:
        logger.error(f"Ошибка при присоединении к чеку: {str(e)}")

        error_message = create_event_status_message("joinBillEventStatus", "error", message=str(e))

        await ws_manager.send_personal_message(
            message=json.dumps(error_message),
            user_id=user_id
        )