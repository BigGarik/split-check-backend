from sqlalchemy.ext.asyncio import AsyncSession

from src.managers.check_manager import CheckManager
from src.redis import queue_processor
from src.schemas import UserProfileUpdate
from src.tasks import add_item_task, add_empty_check_task, delete_item_task, edit_item_task, join_check_task, \
    delete_check_task, split_item_task, send_check_data_task, send_all_checks_task
from src.tasks.image_recognition import recognize_image_task
from src.tasks.user import get_user_profile_task, update_user_profile_task
from src.tasks.user_selection import user_selection_task
from src.utils.db import with_db_session


@with_db_session()
async def handle_recognize_image_task(session: AsyncSession, task_data: dict):
    await recognize_image_task(
        check_uuid=task_data["check_uuid"],
        user_id=task_data["user_id"],
        file_location_directory=task_data["file_location_directory"],
        file_name=task_data["file_name"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_send_all_checks_task(session: AsyncSession, task_data: dict):
    await send_all_checks_task(
        user_id=task_data["user_id"],
        page=task_data["page"],
        page_size=task_data["page_size"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_send_check_data_task(session: AsyncSession, task_data: dict):
    await send_check_data_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_user_selection_task(session: AsyncSession, task_data: dict):
    await user_selection_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        selection_data=task_data["selection_data"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_split_item_task(session: AsyncSession, task_data: dict):
    await split_item_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        item_data=task_data["item_data"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_delete_check_task(session: AsyncSession, task_data: dict):
    await delete_check_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        check_manager=CheckManager(session)
    )


async def handle_get_user_profile_task(task_data: dict):
    await get_user_profile_task(
        user_id=task_data["user_id"]
    )


async def handle_update_user_profile_task(task_data: dict):
    await update_user_profile_task(
        user_id=task_data["user_id"],
        profile_data=UserProfileUpdate(**task_data["profile_data"])
    )


@with_db_session()
async def handle_join_check_task(session: AsyncSession, task_data: dict):
    await join_check_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_add_empty_check_task(session: AsyncSession, task_data: dict):
    await add_empty_check_task(
        user_id=task_data["user_id"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_add_item_task(session: AsyncSession, task_data: dict):
    await add_item_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        item_data=task_data["item_data"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_delete_item_task(session: AsyncSession, task_data: dict):
    await delete_item_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        item_id=task_data["item_id"],
        check_manager=CheckManager(session)
    )


@with_db_session()
async def handle_edit_item_task(session: AsyncSession, task_data: dict):
    await edit_item_task(
        user_id=task_data["user_id"],
        check_uuid=task_data["check_uuid"],
        item_data=task_data["item_data"],
        check_manager=CheckManager(session)
    )


def register_redis_handlers():
    """Регистрируем обработчики для обработки задач из очередей Redis."""

    queue_processor.register_handler("recognize_image_task", handle_recognize_image_task)
    queue_processor.register_handler("send_all_checks_task", handle_send_all_checks_task)
    queue_processor.register_handler("send_check_data_task", handle_send_check_data_task)
    queue_processor.register_handler("user_selection_task", handle_user_selection_task)
    queue_processor.register_handler("split_item_task", handle_split_item_task)
    queue_processor.register_handler("delete_check_task", handle_delete_check_task)
    queue_processor.register_handler("get_user_profile_task", handle_get_user_profile_task)
    queue_processor.register_handler("update_user_profile_task", handle_update_user_profile_task)
    queue_processor.register_handler("join_check_task", handle_join_check_task)
    queue_processor.register_handler("add_empty_check_task", handle_add_empty_check_task)
    queue_processor.register_handler("add_item_task", handle_add_item_task)
    queue_processor.register_handler("delete_item_task", handle_delete_item_task)
    queue_processor.register_handler("edit_item_task", handle_edit_item_task)
