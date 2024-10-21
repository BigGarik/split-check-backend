import os
from loguru import logger
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.crud import get_user_by_email, create_new_user
from app.database import get_async_db

load_dotenv()

templates = Jinja2Templates(directory="templates")

router_user = APIRouter()


@router_user.post("/user/create", response_model=schemas.User)
async def create_user(user: schemas.UserCreate):
    db_user = await get_user_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await create_new_user(user=user)
    return new_user


@router_user.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


if __name__ == '__main__':
    pass
