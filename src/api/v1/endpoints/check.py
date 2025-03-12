from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Query
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.models import User, StatusEnum
from src.redis import queue_processor
from src.schemas import CheckSelectionRequest
from src.utils.db import get_async_db

router = APIRouter()


@router.post("/add", summary="Добавление пустого чека")
async def add_empty_check(request: Request, user: User = Depends(get_current_user)):
    task_data = {
        "type": "add_empty_check_task",
        "user_id": user.id
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.get("/all", summary="Получить все чеки")
async def get_all_check(request: Request,
                        check_name: Optional[str] = None,
                        check_status: Optional[StatusEnum] = None,
                        start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
                        end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format"),
                        page: int = Query(default=1, ge=1),
                        page_size: int = Query(default=20, ge=1, le=100),
                        user: User = Depends(get_current_user)):

    task_data = {
        "type": "send_all_checks_task",
        "user_id": user.id,
        "check_name": check_name,
        "check_status": str(check_status.value) if check_status else None,
        "start_date": str(start_date) if start_date else None,
        "end_date": str(end_date) if end_date else None,
        "page": page,
        "page_size": page_size
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чеков отправлены в очередь для передачи через WebSocket"}


@router.get("/main_page", summary="Получить чеки на главной странице")
async def get_main_page(request: Request, user: User = Depends(get_current_user)):
    task_data = {
        "type": "send_main_page_checks_task",
        "user_id": user.id,
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные главной страницы отправлены в очередь для передачи через WebSocket"}


@router.get("/{uuid}", summary="Получить чек по UUID")
async def get_check(request: Request,
                    uuid: UUID,
                    user: User = Depends(get_current_user),
                    session: AsyncSession = Depends(get_async_db)
                    ):
    # ########    Для теста пидантик
    # async with get_async_db() as session:
    #     query = select(Check).where(Check.uuid == str(uuid))
    #     result = await session.execute(query)
    #     check = result.scalar_one_or_none()
    #
    #     order = Order.model_validate(check.check_data)
    #     print(f"Check UUID: {check.uuid}")
    #     print(f"Order data: {order}")
    #     print(f"total: {order.total}")
    #     # Calculate the sum of all item totals
    #     total_sum = sum(item.price for item in order.items)
    #     print(f"Sum of all item totals: {total_sum}")
    # #########

    task_data = {
        "type": "send_check_data_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }

    await queue_processor.push_task(task_data)

    return {"message": "Данные чека отправлены в очередь для передачи через WebSocket"}


@router.post("/{uuid}/select", summary="Выбор пользователя")
async def user_selection(request: Request,
                         uuid: UUID,
                         selection: CheckSelectionRequest,
                         user: User = Depends(get_current_user)):
    task_data = {
        "type": "user_selection_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "selection_data": selection.model_dump()
    }
    await queue_processor.push_task(task_data)

    return {"message": "Данные о выборе отправлены в очередь для передачи через WebSocket"}


@router.post("/name", summary="Изменение названия чека")
async def edit_check_name(request: Request,
                          uuid: UUID,
                          check_name: str,
                          user: User = Depends(get_current_user)):
    task_data = {
        "type": "edit_check_name_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
        "check_name": check_name
    }
    await queue_processor.push_task(task_data)

    return {"message": "Данные отправлены в очередь для передачи через WebSocket"}


@router.post(
    "/status",
    summary="Изменение статуса чека",
    description="Эндпоинт для изменения статуса чека. "
                "Допустимые значения статуса: 'OPEN', 'CLOSE'.",
    response_description="Сообщение о том, что данные отправлены в очередь."
)
async def edit_check_status(
        request: Request,
        uuid: UUID,
        check_status: StatusEnum,
        user: User = Depends(get_current_user),
):
    """
    Изменяет статус чека и отправляет задачу в очередь для последующей обработки через WebSocket.

    **Параметры запроса:**
    - `uuid`: Уникальный идентификатор чека.
    - `check_status`: Новый статус чека. Допустимые значения: 'OPEN', 'CLOSE'.

    **Авторизация:**
    Пользователь должен быть аутентифицирован (передавать токен через заголовок Authorization).

    **Пример ответа:**
    ```json
    {
        "message": "Данные отправлены в очередь для передачи через WebSocket"
    }
    ```

    :param check_status:
    :param uuid:
    :param request: Данные для изменения статуса чека.
    :param user: Текущий пользователь, извлекаемый через Depends(get_current_user).
    :return: Сообщение об успешной отправке данных.
    """
    task_data = {
        "type": "edit_check_status_task",
        "user_id": user.id,
        "check_uuid": uuid,
        "check_status": check_status.value
    }
    await queue_processor.push_task(task_data)

    return {"message": "Данные отправлены в очередь для передачи через WebSocket"}


@router.post("/join", summary="Присоединение пользователя к чеку")
async def join_check(request: Request,
                     uuid: UUID,
                     user: User = Depends(get_current_user)):
    """Присоединяет пользователя к чеку и возвращает статус операции."""
    task_data = {
        "type": "join_check_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для присоединения отправлены в очередь"}


@router.delete("/delete", summary="Удаление чека")
async def delete_check(request: Request,
                       uuid: UUID,
                       user: User = Depends(get_current_user)):
    """Удаляет чек."""
    task_data = {
        "type": "delete_check_task",
        "user_id": user.id,
        "check_uuid": str(uuid),
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для удаления отправлены в очередь"}


@router.delete("/user/delete", summary="Удаление пользователя из чека")
async def user_delete_from_check(request: Request,
                                 uuid: UUID,
                                 user_id_for_delite,
                                 user: User = Depends(get_current_user)):
    """Удаляет пользователя из чека.

    """
    task_data = {
        "type": "user_delete_from_check_task",
        "check_uuid": str(uuid),
        "user_id_for_delite": user_id_for_delite,
        "current_user_id": user.id,
    }
    await queue_processor.push_task(task_data)
    return {"message": "Данные для удаления отправлены в очередь"}
