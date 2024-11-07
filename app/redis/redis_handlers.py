# redis_handlers.py
from app.tasks import add_item_task, add_empty_check_task, delete_item_task, edit_item_task, join_check_task, \
    delete_check_task, split_item_task, send_check_data_task, send_all_checks_task
from app.tasks.image_recognition import recognize_image_task
from app.tasks.user_selection import user_selection_task
from app.tasks.user import get_user_profile_task, update_user_profile_task
from app.schemas import UserProfileUpdate
from app.redis import queue_processor
from app.redis import redis_client


def register_redis_handlers():
    """Регистрируем обработчики для обработки задач из очередей Redis."""

    queue_processor.register_handler("recognize_image_task", lambda task_data: recognize_image_task(
        task_data["check_uuid"],
        task_data["user_id"],
        task_data["file_location_directory"],
        task_data["file_name"],
        redis_client
    ))
    queue_processor.register_handler("send_all_checks_task", lambda task_data: send_all_checks_task(
        task_data["user_id"],
        task_data["page"],
        task_data["page_size"]
    ))
    queue_processor.register_handler("send_check_data_task", lambda task_data: send_check_data_task(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("user_selection_task", lambda task_data: user_selection_task(
        task_data["user_id"],
        task_data["check_uuid"],
        task_data["selection_data"]
    ))
    queue_processor.register_handler("split_item_task", lambda task_data: split_item_task(
        task_data["user_id"],
        task_data["check_uuid"],
        task_data["item_id"],
        task_data["quantity"],
    ))
    queue_processor.register_handler("delete_check_task", lambda task_data: delete_check_task(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("get_user_profile_task", lambda task_data: get_user_profile_task(
        task_data["user_id"],
    ))
    queue_processor.register_handler("update_user_profile_task", lambda task_data: update_user_profile_task(
        task_data["user_id"],
        UserProfileUpdate(**task_data["profile_data"]),
    ))
    queue_processor.register_handler("join_check_task", lambda task_data: join_check_task(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("add_empty_check_task", lambda task_data: add_empty_check_task(
        task_data["user_id"]
    ))
    queue_processor.register_handler("add_item_task", lambda task_data: add_item_task(
        task_data["user_id"],
        task_data["item_data"]
    ))
    queue_processor.register_handler("delete_item_task", lambda task_data: delete_item_task(
        task_data["user_id"],
        task_data["item_data"]
    ))
    queue_processor.register_handler("edit_item_task", lambda task_data: edit_item_task(
        task_data["user_id"],
        task_data["item_data"]
    ))
