import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.config import config
from src.models import User
from src.repositories.check import get_all_checks_for_admin, get_check_data, get_check_by_uuid
from src.repositories.user_selection import get_user_selection_by_check_uuid
from src.utils.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates/webui")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")


# @router.get("", response_class=HTMLResponse)
# async def get_home_redirect():
#     # Редирект на главную страницу, она вызывает fetch с токеном
#     return RedirectResponse(url="/api/v2/webui/home", status_code=307)


@router.get("/")
async def get_home_page(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/websocket")
async def websocket(request: Request):
    return templates.TemplateResponse("websocket.html", {"request": request})


@router.get("/users")
async def users(request: Request, user: User = Depends(get_current_user)):
    return templates.TemplateResponse("users.html", {"request": request})


@router.get("/checks")
async def checks(request: Request,
                session: AsyncSession = Depends(get_session),
                user: User = Depends(get_current_user),
                user_id: Optional[int] = Query(None),
                email: Optional[str] = Query(None),
                page: int = Query(1, ge=1),
                page_size: int = Query(10, ge=1),
                check_name: Optional[str] = Query(None),
                check_status: Optional[str] = Query(None),
                start_date: Optional[str] = Query(None),
                end_date: Optional[str] = Query(None),
                restaurant: Optional[str] = Query(None),
                author_id: Optional[int] = Query(None),
                currency: Optional[str] = Query(None),):
    if user.id not in config.app.admin_ids:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized")

    result = await get_all_checks_for_admin(session=session,
                                            user_id=user_id,
                                            email=email,
                                            page=page,
                                            page_size=page_size,
                                            check_name=check_name,
                                            check_status=check_status,
                                            start_date=start_date,
                                            end_date=end_date,
                                            restaurant=restaurant,
                                            author_id=author_id,
                                            currency=currency
                                        )

    return templates.TemplateResponse("checks.html", {
        "request": request,
        "checks": result["checks"],
        "page": result["page"],
        "total_pages": result["total_pages"],
        "filters": {
            "user_id": user_id,
            "email": email,
            "check_name": check_name,
            "check_status": check_status,
            "start_date": start_date,
            "end_date": end_date,
            "restaurant": restaurant,
            "author_id": author_id,
            "currency": currency,
        }
    })


@router.get("/checks/{uuid}", response_class=HTMLResponse)
async def check_detail_page(
    request: Request,
    uuid: UUID,
    session: AsyncSession = Depends(get_session)
):
    try:
        check_uuid = str(uuid)
        check_data = await get_check_data(session, check_uuid)

        logger.debug(f"check_data: {check_data}")

        participants, user_selections, _ = await get_user_selection_by_check_uuid(session, check_uuid)

        check_data["participants"] = json.loads(participants)
        check_data["user_selections"] = json.loads(user_selections)
        check = await get_check_by_uuid(session, check_uuid)
        check_data["name"] = check.name
        check_data["date"] = check.created_at.strftime("%d.%m.%Y")
        check_data["uuid"] = check_uuid
        check_data["author_id"] = check.author_id
        check_data["status"] = check.status.value

    except Exception as e:
        logger.error(f"Ошибка при отправке чека: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )

    return templates.TemplateResponse(
        "check_detail.html",
        {"request": request, "check_data": check_data, "uuid": uuid}
    )


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})
