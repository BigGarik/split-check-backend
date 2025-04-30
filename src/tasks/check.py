import json
import logging
import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import REDIS_EXPIRATION
from src.config.type_events import Events
from src.managers.check_manager import CheckManager, get_check_manager
from src.redis import redis_client
from src.repositories.check import get_check_data_from_database, get_all_checks, get_main_page_checks, \
    add_check_to_database, edit_check_name_to_database
from src.repositories.user import get_users_by_check_uuid
from src.repositories.user_selection import get_user_selection_by_check_uuid
from src.utils.notifications import create_event_message, create_event_status_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(__name__)


# refac
async def send_check_data_task(user_id: int, check_uuid: str, session: AsyncSession):

    redis_key = f"check_uuid:{check_uuid}"
    logger.debug(f"redis_key: {redis_key}")

    # Попытка получить данные из Redis
    check_data = await redis_client.get(redis_key)

    if check_data:
        logger.debug(f"check_data from redis: {check_data}")
        if isinstance(check_data, (str, bytes, bytearray)):
            check_data = json.loads(check_data)
    else:
        check_data = await get_check_data_from_database(session, check_uuid)
        logger.debug(f"check_data from DB: {check_data}")
    participants, user_selections, _ = await get_user_selection_by_check_uuid(session, check_uuid)

    logger.debug(f"participants: {json.loads(participants)}")
    logger.debug(f"user_selections: {json.loads(user_selections)}")

    check_data["participants"] = json.loads(participants)
    check_data["user_selections"] = json.loads(user_selections)

    msg = create_event_message(
        message_type=Events.BILL_DETAIL_EVENT,
        payload=check_data
    )

    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


# refac
async def send_all_checks_task(user_id: int, page: int, page_size: int, session: AsyncSession, check_name: Optional[str] = None, check_status: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None):
    checks_data = await get_all_checks(session,
                                       user_id=user_id,
                                       page=page,
                                       page_size=page_size,
                                       check_name=check_name,
                                       check_status=check_status,
                                       start_date=start_date,
                                       end_date=end_date)
    msg = create_event_message(
        message_type=Events.ALL_BILL_EVENT,
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
    logger.debug(f"Страница все чеки: {msg}")

    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


# refac
async def send_main_page_checks_task(user_id: int, session: AsyncSession):

    checks_data = await get_main_page_checks(session, user_id)

    msg = create_event_message(
        message_type=Events.MAIN_PAGE_EVENT,
        payload={
            "checks": checks_data["items"],
            "total_open": checks_data["total_open"],
            "total_closed": checks_data["total_closed"],
        }
    )
    logger.debug(f"Главная страница: {msg}")
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


# refac
async def add_empty_check_task(user_id: int, session: AsyncSession):
    check_uuid = str(uuid.uuid4())

    await add_check_to_database(session, check_uuid, user_id)

    msg = create_event_message(
        message_type=Events.CHECK_ADD_EVENT,
        payload={"uuid": check_uuid}
    )
    await ws_manager.send_personal_message(
        message=json.dumps(msg),
        user_id=user_id
    )


# refac
async def edit_check_name_task(user_id: int, check_uuid: str, check_name: str, session: AsyncSession):

    new_name_status = await edit_check_name_to_database(session, user_id, check_uuid, check_name)
    users = await get_users_by_check_uuid(session, check_uuid)

    if new_name_status == "Check name updated successfully.":
        msg_for_author = create_event_status_message(
            message_type=Events.CHECK_NAME_EVENT_STATUS,
            status="success"
        )

        msg_for_all = create_event_message(
            message_type=Events.CHECK_NAME_EVENT,
            payload={"check_name": check_name},
        )
        all_user_ids = {user.id for user in users}
        logger.debug(f"Все пользователи для отправки: {all_user_ids}")

        # Отправка сообщений всем пользователям
        for uid in all_user_ids:
            msg = msg_for_author if uid == user_id else msg_for_all
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg),
                    user_id=user_id
                )
            except Exception as e:
                logger.warning(f"Ошибка отправки сообщения пользователю {uid}: {str(e)}")


async def edit_check_status_task(user_id: int,
                                 check_uuid: str,
                                 check_status: str,
                                 check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.edit_check_status(user_id, check_uuid, check_status)


async def join_check_task(user_id: int,
                          check_uuid: str,
                          check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.join_check(user_id, check_uuid)


async def delete_check_task(user_id: int,
                            check_uuid: str,
                            check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.delete_check(user_id, check_uuid)


async def user_delete_from_check_task(check_uuid: str,
                                      user_id_for_delete: int,
                                      current_user_id: int,
                                      check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.user_delete_from_check(check_uuid, user_id_for_delete, current_user_id)
