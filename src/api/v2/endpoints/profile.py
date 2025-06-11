import logging

from fastapi import APIRouter, Depends, Request
from starlette import status
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from src.api.deps import get_current_user
from src.models.user import User
from src.repositories.profile import get_user_profile_db, get_user_email, update_user_profile_db
from src.schemas import UserProfileUpdate, UserProfileResponse, UserProfileBase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/profile",
    summary="Получить профиль пользователя. Синхронный ответ",
    description="Возвращает профиль текущего пользователя.",
    response_model=UserProfileBase,
    status_code=status.HTTP_200_OK
)
async def get_profile(
    request: Request,
    user: User = Depends(get_current_user)
) -> JSONResponse:
    """Получить профиль текущего пользователя."""
    profile = await get_user_profile_db(user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Профиль не найден")

    profile_response = UserProfileResponse.model_validate(profile)
    email = await get_user_email(user.id)
    profile_payload = profile_response.model_dump(mode="json")
    profile_payload['email'] = email

    return JSONResponse(status_code=200, content=profile_payload)


@router.put(
    "/profile",
    summary="Обновить профиль пользователя. Синхронный ответ",
    description="Обновляет профиль текущего пользователя.",
    response_model=UserProfileBase,
    status_code=status.HTTP_200_OK
)
async def update_profile(
    request: Request,
    profile_data: UserProfileUpdate,
    user: User = Depends(get_current_user)
):
    """Обновить профиль текущего пользователя."""
    updated = await update_user_profile_db(user.id, profile_data)
    if not updated:
        raise HTTPException(status_code=404, detail="Не удалось обновить профиль")

    profile_response = UserProfileResponse.model_validate(updated)
    return profile_response.model_dump(include={"nickname", "language", "avatar_url"})
