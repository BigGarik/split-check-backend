import uuid
from datetime import date
from typing import Optional

from fastapi import Depends

from src.managers.check_manager import CheckManager, get_check_manager
from src.models import StatusEnum


async def send_check_data_task(user_id: int,
                               check_uuid: str,
                               check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_check_data(user_id, check_uuid)


async def send_all_checks_task(user_id: int,
                               page: int,
                               page_size: int,
                               check_name: Optional[str] = None,
                               check_status: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_all_checks(
                                        user_id=user_id,
                                        page=page,
                                        page_size=page_size,
                                        check_name=check_name,
                                        check_status=check_status,
                                        start_date=start_date,
                                        end_date=end_date
                                        )


async def send_main_page_checks_task(user_id: int,
                                     check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_main_page_checks(user_id)


async def add_empty_check_task(user_id: int,
                               check_manager: CheckManager = Depends(get_check_manager)):
    check_uuid = str(uuid.uuid4())
    await check_manager.create_empty(user_id, check_uuid)


async def edit_check_name_task(user_id: int,
                               check_uuid: str,
                               check_name: str,
                               check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.edit_check_name(user_id, check_uuid, check_name)


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
                                      user_id_for_delite: int,
                                      current_user_id: int,
                                      check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.user_delete_from_check(check_uuid, user_id_for_delite, current_user_id)
