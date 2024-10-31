# redis_handlers.py

from app.tasks.image_recognition import recognize_image
from app.tasks.receipt_processing import send_all_checks, send_check_data, send_check_selection, split_item, \
    check_delete
from app.tasks.user import get_user_profile, update_user_profile
from app.schemas import UserProfileUpdate
from app.redis import queue_processor
from app.redis import redis_client


def register_redis_handlers():
    """Регистрируем обработчики для обработки задач из очередей Redis."""

    queue_processor.register_handler("recognize_image", lambda task_data: recognize_image(
        task_data["payload"].get("check_uuid", ""),
        task_data["user_id"],
        task_data["payload"].get("file_location_directory", ""),
        task_data["payload"].get("file_name", ""),
        redis_client
    ))
    queue_processor.register_handler("send_all_checks", lambda task_data: send_all_checks(
        task_data["user_id"],
        task_data["page"],
        task_data["page_size"]
    ))
    queue_processor.register_handler("send_check_data", lambda task_data: send_check_data(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("send_check_selection", lambda task_data: send_check_selection(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("split_item", lambda task_data: split_item(
        task_data["user_id"],
        task_data["check_uuid"],
        task_data["item_id"],
        task_data["quantity"],
    ))
    queue_processor.register_handler("check_delete", lambda task_data: check_delete(
        task_data["user_id"],
        task_data["check_uuid"],
    ))
    queue_processor.register_handler("get_user_profile", lambda task_data: get_user_profile(
        task_data["user_id"],
    ))
    queue_processor.register_handler("update_user_profile", lambda task_data: update_user_profile(
        task_data["user_id"],
        UserProfileUpdate(**task_data["profile_data"]),
    ))

