from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.exc import DatabaseError

from app.redis import queue_processor
from app import schemas
from app.auth import get_current_user
from app.crud import create_new_user
from app.models import User
from app.schemas.user import UserProfileUpdate

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/create", response_model=schemas.User)
async def create_user(user_data: schemas.UserCreate):

    try:
        new_user = await create_new_user(user_data=user_data)
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail="Database error occurred")


@router.get("/profile")
async def get_profile(current_user: Annotated[User, Depends(get_current_user)]):

    task_data = {
        "type": "get_user_profile_task",
        "user_id": current_user.id
    }

    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}


@router.put("/profile")
async def update_profile(profile_data: UserProfileUpdate,
                         user: Annotated[User, Depends(get_current_user)]):

    profile_data_dict = profile_data.model_dump()

    task_data = {
        "type": "update_user_profile_task",
        "user_id": user.id,
        "profile_data": profile_data_dict
    }

    await queue_processor.push_task(task_data)
    return {"message": "Данные отправлены в WebSocket"}
