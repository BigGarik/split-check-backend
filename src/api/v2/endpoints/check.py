import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.models import User, StatusEnum
from src.repositories.check import get_main_page_checks, get_all_checks, get_check_data
from src.utils.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/mainPage", summary="Получить чеки на главной странице")
async def get_main_page(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    try:
        checks_data = await get_main_page_checks(session, user.id)

        payload = {
            "checks": checks_data["items"],
            "total_open": checks_data["total_open"],
            "total_closed": checks_data["total_closed"],
        }
        logger.debug(f"Отправлены данные главной страницы для пользователя ИД {user.id}: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Ошибка при отправке главной страницы: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@router.get("/", summary="Получить все чеки")
async def get_all_check(
                        check_name: Optional[str] = None,
                        check_status: Optional[StatusEnum] = None,
                        start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
                        end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format"),
                        page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=20, ge=1, le=100),
                        user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    try:
        checks_data = await get_all_checks(session,
                                           user_id=user.id,
                                           page=page,
                                           page_size=page_size,
                                           check_name=check_name,
                                           check_status=check_status,
                                           start_date=start_date,
                                           end_date=end_date)

        payload = {
            "checks": checks_data["items"],
            "pagination": {
                "total": checks_data["total"],
                "page": checks_data["page"],
                "pageSize": checks_data["page_size"],
                "totalPages": checks_data["total_pages"]
            }
        }
        logger.debug(f"Отправлены данные всех чеков для пользователя ИД {user.id}: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Ошибка при отправке всех чеков: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )


@router.get("/{uuid}", summary="Получить чек по UUID", response_model=None)
async def get_check(
                    uuid: UUID,
                    user: User = Depends(get_current_user),
                    session: AsyncSession = Depends(get_session)
                    ):
    try:
        check_data = await get_check_data(session, user.id, str(uuid))

        logger.debug(f"Отправлены данные чека для пользователя ИД {user.id}: {check_data}")
        return check_data

    except Exception as e:
        logger.error(f"Ошибка при отправке чека: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении данных: {str(e)}"
        )
