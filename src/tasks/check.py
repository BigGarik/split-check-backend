import uuid

from fastapi import Depends

from src.managers.check_manager import CheckManager, get_check_manager


async def send_check_data_task(user_id: int,
                               check_uuid: str,
                               check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_check_data(user_id, check_uuid)


async def send_all_checks_task(user_id: int,
                               page: int = 1,
                               page_size: int = 10,
                               check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_all_checks(user_id, page, page_size)


async def send_main_page_checks_task(user_id: int,
                                     check_manager: CheckManager = Depends(get_check_manager)):
    await check_manager.send_main_page_checks(user_id)


async def add_empty_check_task(user_id: int,
                               check_manager: CheckManager = Depends(get_check_manager)):
    check_uuid = str(uuid.uuid4())
    await check_manager.create_empty(user_id, check_uuid)


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
