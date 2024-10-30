from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from app.redis import queue_processor
from app import schemas
from app.auth import get_current_user
from app.crud import get_user_by_email, create_new_user
from app.models import User
from app.schemas.user import UserProfileUpdate, UserProfileResponse

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/create", response_model=schemas.User)
async def create_user(user: schemas.UserCreate):
    db_user = await get_user_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_new_user(user=user)
    return new_user


@router.get("/profile")
async def get_profile(
        current_user: Annotated[User, Depends(get_current_user)]
):
    task_data = {
        "type": "get_user_profile",
        "user_id": current_user.id
    }

    await queue_processor.push_task(task_data)
    # return {"message": "Данные отправлены в WebSocket"}


@router.put("/profile")
async def update_profile(
        profile_data: UserProfileUpdate,
        current_user: Annotated[User, Depends(get_current_user)]
):
    profile_data_dict = profile_data.model_dump()

    task_data = {
        "type": "update_user_profile",
        "user_id": current_user.id,
        "profile_data": profile_data_dict
    }

    await queue_processor.push_task(task_data)
    # return {"message": "Данные отправлены в WebSocket"}



# # Получение профиля
# response = await client.get(
#     "/profile",
#     headers={"Authorization": f"Bearer {token}"}
# )
#
# # Обновление профиля
# response = await client.put(
#     "/profile",
#     headers={"Authorization": f"Bearer {token}"},
#     json={
#         "nickname": "John Doe",
#         "language": "en",
#         "avatar_url": "https://example.com/avatar.jpg"
#     }
# )
