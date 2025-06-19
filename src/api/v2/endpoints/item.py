import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.exceptions import HTTPException

from src.api.deps import get_current_user
from src.config import config
from src.config.type_events import Events
from src.models import User
from src.repositories.check import get_check_data_from_database
from src.repositories.item import add_item_to_check, update_item_quantity, edit_item_in_check, remove_item_from_check
from src.repositories.user import get_users_by_check_uuid
from src.schemas import AddItemRequest, EditItemRequestV2
from src.utils.db import get_session
from src.utils.notifications import create_event_message
from src.websockets.manager import ws_manager

logger = logging.getLogger(config.app.service_name)

router = APIRouter()


@router.post(
    "/{uuid}/items/add",
    summary="Добавление позиции в чек. Синхронный ответ",
    description="Добавляет новую позицию в указанный чек. Все участники получают уведомление по WebSocket.",
    response_model=dict,
    response_description="Добавленная позиция и UUID чека",
    status_code=status.HTTP_201_CREATED
)
async def add_item(
    request: Request,
    item_data: AddItemRequest,
    uuid: UUID = Path(..., description="UUID чека"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Добавляет новую позицию в указанный чек.

    - **uuid**: UUID чека.
    - **item_data**: Информация о добавляемой позиции.
    - **user**: Автор запроса.
    """
    check_uuid = str(uuid)

    try:
        users = await get_users_by_check_uuid(session, check_uuid)
        new_item = await add_item_to_check(session, check_uuid, item_data)

        # Принудительное обновление данных чека (и кеша, если применяется Redis)
        await get_check_data_from_database(session, check_uuid)

        msg_for_all = create_event_message(
            message_type=Events.ITEM_ADD_EVENT,
            payload={"uuid": check_uuid, "item": new_item}
        )

        all_user_ids = {u.id for u in users}

        for uid in all_user_ids:
            try:
                await ws_manager.send_personal_message(
                    message=json.dumps(msg_for_all),
                    user_id=uid
                )
            except Exception as e:
                logger.warning(
                    f"Ошибка отправки WS сообщения пользователю {uid}: {str(e)}",
                    extra={"initiator": user.id, "check_uuid": check_uuid}
                )

        logger.info(
            f"Позиция добавлена в чек {check_uuid} пользователем {user.id}",
            extra={"item_id": new_item.get('id'), "check_uuid": check_uuid}
        )

        return {
            "uuid": check_uuid,
            "item": new_item
        }

    except Exception as e:
        logger.exception(
            f"Ошибка при добавлении позиции в чек {check_uuid}: {str(e)}",
            extra={"initiator": user.id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка сервера при добавлении позиции в чек."
        )


@router.put(
    "/{uuid}/items/{item_id}/split",
    summary="Разделение позиции в чеке. Синхронный ответ",
    description="Разделяет позицию на указанное количество частей.",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def split_item(
    request: Request,
    item_id: int = Path(..., description="ID позиции"),
    quantity: int = Query(..., gt=0, le=1000, description="Новое количество товара (от 1 до 1000)"),
    uuid: UUID = Path(..., description="UUID чека"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    check_uuid = str(uuid)
    try:
        await update_item_quantity(session, check_uuid, item_id, quantity)
        await get_check_data_from_database(session, check_uuid)
        users = await get_users_by_check_uuid(session, check_uuid)

        msg = create_event_message(
            message_type=Events.ITEM_SPLIT_EVENT,
            payload={"check_uuid": check_uuid, "item_id": item_id, "quantity": quantity}
        )

        for uid in {u.id for u in users}:
            try:
                await ws_manager.send_personal_message(json.dumps(msg), user_id=uid)
            except Exception as e:
                logger.warning(f"WS split send error to {uid}: {e}", extra={"user": user.id})

        logger.info(f"Item {item_id} split in check {check_uuid}", extra={"user": user.id})
        return {"check_uuid": check_uuid, "item_id": item_id, "quantity": quantity}

    except Exception as e:
        logger.exception("Split item error", extra={"user": user.id})
        raise HTTPException(status_code=500, detail="Ошибка при разделении позиции")


@router.put(
    "/{uuid}/items/{item_id}/edit",
    summary="Редактирование позиции. Синхронный ответ",
    description="Изменяет данные позиции и отправляет обновления всем участникам.",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def edit_item(
    request: Request,
    item_data: EditItemRequestV2,
    item_id: int = Path(..., description="ID позиции"),
    uuid: UUID = Path(..., description="UUID чека"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    check_uuid = str(uuid)
    try:
        data = item_data.model_dump()
        data["id"] = item_id
        updated_data = await edit_item_in_check(session, check_uuid, data)
        await get_check_data_from_database(session, check_uuid)
        users = await get_users_by_check_uuid(session, check_uuid)

        msg = create_event_message(
            message_type=Events.ITEM_EDIT_EVENT,
            payload={"uuid": check_uuid, "new_check_data": updated_data}
        )

        for uid in {u.id for u in users}:
            try:
                await ws_manager.send_personal_message(json.dumps(msg), user_id=uid)
            except Exception as e:
                logger.warning(f"WS edit send error to {uid}: {e}", extra={"current_user_id": user.id})

        logger.info(f"Item edited in check {check_uuid}", extra={"current_user_id": user.id})
        return {"uuid": check_uuid, "updated_data": updated_data}

    except Exception as e:
        logger.exception("Edit item error", extra={"current_user_id": user.id})
        raise HTTPException(status_code=500, detail="Ошибка при редактировании позиции")


@router.delete(
    "/{uuid}/items/{item_id}",
    summary="Удаление позиции. Синхронный ответ",
    description="Удаляет позицию из чека и рассылает событие участникам.",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def delete_item(
    request: Request,
    item_id: int = Path(..., description="ID позиции для удаления"),
    uuid: UUID = Path(..., description="UUID чека"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    check_uuid = str(uuid)
    try:
        await remove_item_from_check(session, check_uuid, item_id)
        await get_check_data_from_database(session, check_uuid)
        users = await get_users_by_check_uuid(session, check_uuid)

        msg = create_event_message(
            message_type=Events.ITEM_REMOVE_EVENT,
            payload={"uuid": check_uuid, "item_id": item_id}
        )

        for uid in {u.id for u in users}:
            try:
                await ws_manager.send_personal_message(json.dumps(msg), user_id=uid)
            except Exception as e:
                logger.warning(f"WS delete send error to {uid}: {e}", extra={"user": user.id})

        logger.info(f"Item {item_id} deleted from check {check_uuid}", extra={"user": user.id})
        return {"uuid": check_uuid, "item_id": item_id}

    except Exception as e:
        logger.exception("Delete item error", extra={"user": user.id})
        raise HTTPException(status_code=500, detail="Ошибка при удалении позиции")
