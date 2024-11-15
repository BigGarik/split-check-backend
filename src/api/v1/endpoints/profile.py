from typing import Annotated

from fastapi import APIRouter, Depends
from loguru import logger
from src.api.deps import get_current_user
from src.models.user import User
from src.redis import queue_processor
from src.schemas import UserProfileUpdate

router = APIRouter()


@router.get("/profile")
async def get_profile(user: Annotated[User, Depends(get_current_user)]):

    task_data = {
        "type": "get_user_profile_task",
        "user_id": user.id
    }
    logger.debug(f"user_id: {user.id}")
    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}


@router.put("/profile")
async def update_profile(profile_data: UserProfileUpdate,
                         user: Annotated[User, Depends(get_current_user)]):

    profile_data_dict = profile_data.model_dump()
    logger.debug(f"user_id: {user.id}")
    task_data = {
        "type": "update_user_profile_task",
        "user_id": user.id,
        "profile_data": profile_data_dict
    }

    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}
