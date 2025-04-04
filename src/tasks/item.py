from fastapi import Depends

from src.managers.check_manager import CheckManager, get_check_manager


async def add_item_task(user_id: int,
                        check_uuid: str,
                        item_data: dict,
                        check_manager: CheckManager = Depends(get_check_manager)):

    await check_manager.add_item(user_id, check_uuid, item_data)


async def delete_item_task(user_id: int,
                           check_uuid: str,
                           item_id: int,
                           check_manager: CheckManager = Depends(get_check_manager)):

    await check_manager.delete_item(user_id, check_uuid, item_id)


async def edit_item_task(user_id: int,
                         check_uuid: str,
                         item_data: dict,
                         check_manager: CheckManager = Depends(get_check_manager)):

    await check_manager.edit_item(user_id, check_uuid, item_data)


async def split_item_task(user_id: int,
                          check_uuid: str,
                          item_data: dict,
                          check_manager: CheckManager = Depends(get_check_manager)):

    await check_manager.split_item(user_id, check_uuid, item_data)


async def convert_check_currency_task(check_uuid: str,
                                    target_currency: str,
                                    user_id: int,
                                    check_manager: CheckManager = Depends(get_check_manager)):

    await check_manager.convert_check_currency(check_uuid, target_currency, user_id)