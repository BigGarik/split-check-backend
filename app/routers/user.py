from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException

from app import schemas
from app.auth import get_current_user
from app.crud import get_user_by_email, create_new_user
from app.crud.user import get_user_profile, create_user_profile, update_user_profile
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


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
        current_user: Annotated[User, Depends(get_current_user)]
):
    """Получить профиль текущего пользователя"""
    profile = await get_user_profile(current_user.id)
    if not profile:
        # Если профиля нет, создаем пустой
        profile = await create_user_profile(current_user.id, UserProfileUpdate())
    return profile


@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
        profile_data: UserProfileUpdate,
        current_user: Annotated[User, Depends(get_current_user)]
):
    """Обновить профиль текущего пользователя"""
    profile = await get_user_profile(current_user.id)
    if not profile:
        # Если профиля нет, создаем новый
        profile = await create_user_profile(current_user.id, profile_data)
    else:
        # Если профиль есть, обновляем его
        profile = await update_user_profile(profile, profile_data)
    return profile

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
