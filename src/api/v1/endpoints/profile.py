from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.api.deps import get_current_user
from src.models.user import User
from src.redis.queue_processor import get_queue_processor
from src.schemas import UserProfileUpdate

queue_processor = get_queue_processor()

router = APIRouter()


@router.get("/profile", summary="Получить профиль пользователя")
async def get_profile(request: Request,
                      user: Annotated[User, Depends(get_current_user)]):

    task_data = {
        "type": "get_user_profile_task",
        "user_id": user.id
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}


@router.put("/profile", summary="Обновить профиль пользователя")
async def update_profile(request: Request,
                         profile_data: UserProfileUpdate,
                         user: Annotated[User, Depends(get_current_user)]):
    profile_dict = profile_data.model_dump(exclude_unset=True)
    serialized_profile_dict = UserProfileUpdate.model_validate(profile_dict).model_dump_json()

    task_data = {
        "type": "update_user_profile_task",
        "user_id": user.id,
        "profile_data": serialized_profile_dict
    }

    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}
