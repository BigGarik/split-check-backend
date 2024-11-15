from fastapi import Depends

from src.managers.check_manager import CheckManager, get_check_manager


async def user_selection_task(user_id: int,
                              check_uuid: str,
                              selection_data: dict,
                              check_manager: CheckManager = Depends(get_check_manager)):
    """
    Обновляет выбор пользователя и отправляет обновленную информацию всем связанным пользователям.

    :param check_manager:
    :param user_id: Идентификатор пользователя
    :param check_uuid: UUID чека
    :param selection_data: Данные выбора для сохранения
    """

    await check_manager.handle_user_selection(user_id, check_uuid, selection_data)

    # logger.debug(f"user_selection_task: {user_id}, {check_uuid}, {selection_data}")
    # try:
    #     # Обновляем или добавляем выбор пользователя
    #     await add_or_update_user_selection(user_id=user_id, check_uuid=check_uuid, selection_data=selection_data)
    #
    #     # Получаем участников и пользователей, связанных с чеком
    #     participants, users = await get_user_selection_by_check_uuid(check_uuid)
    #     selections = {
    #         "user_id": user_id,
    #         "selected_items": selection_data['selected_items']
    #     }
    #     logger.info(f"selection_data: {selections}")
    #
    #     logger.debug(f"Участники: {participants}")
    #
    #     # Формируем сообщения
    #     msg_for_all = create_event_message(message_type=settings.Events.CHECK_SELECTION_EVENT,
    #                                        payload={"uuid": check_uuid, "participants": [selections]},
    #                                        )
    #     msg_for_author = create_event_status_message(message_type=settings.Events.CHECK_SELECTION_EVENT_STATUS,
    #                                                  status="success")
    #
    #     # Получаем все user_id для рассылки сообщений
    #     extra_user_ids = {2, 3, 5, 6}
    #     all_user_ids = {user.id for user in users} | extra_user_ids
    #     logger.debug(f"Все пользователи для отправки: {all_user_ids}")
    #
    #     # Отправка сообщений всем пользователям
    #     for uid in all_user_ids:
    #         msg = msg_for_author if uid == user_id else msg_for_all
    #         try:
    #             await ws_manager.send_personal_message(
    #                 message=json.dumps(msg),
    #                 user_id=uid)
    #         except Exception as e:
    #             logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")
    #
    # except Exception as e:
    #     # Логируем ошибку и отправляем инициатору сообщение об ошибке
    #     logger.error(f"Ошибка при выполнении задачи выбора пользователя: {str(e)}")
    #
    #     error_message = create_event_status_message(message_type=settings.Events.CHECK_SELECTION_EVENT_STATUS,
    #                                                 status="error",
    #                                                 message="Ошибка при обработке")
    #     await ws_manager.send_personal_message(
    #         message=json.dumps(error_message),
    #         user_id=user_id
    #     )
    #










