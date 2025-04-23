# src/api/v1/endpoints/avatars.py
import logging
import os
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from starlette.responses import JSONResponse

from src.api.deps import get_current_user
from src.config import BASE_URL
from src.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


AVATAR_DIR = "images/avatars"
AVATAR_URL_PREFIX = f"{BASE_URL}/images/avatars"

# Ensure directory exists
os.makedirs(AVATAR_DIR, exist_ok=True)


@router.post("/upload", summary="Загрузка нескольких аватаров")
async def upload_avatars(
    files: List[UploadFile] = File(...),
    # user: User = Depends(get_current_user)
):
    """Загружает несколько изображений и сохраняет их на диск."""
    try:
        allowed_content_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        max_size = 1024 * 1024  # 1MB

        urls = []

        for file in files:
            if file.content_type not in allowed_content_types:
                logger.warning(f"Пропущен файл {file.filename}: неподдерживаемый тип {file.content_type}")
                continue

            file_data = await file.read()

            if len(file_data) > max_size:
                logger.warning(f"Пропущен файл {file.filename}: превышен размер {len(file_data)}")
                continue

            save_path = os.path.join(AVATAR_DIR, file.filename)
            with open(save_path, "wb") as f:
                f.write(file_data)

            file_url = f"{AVATAR_URL_PREFIX}/{file.filename}"
            urls.append(file_url)

        if not urls:
            raise HTTPException(
                status_code=400,
                detail="Ни один файл не был загружен. Проверьте типы и размеры файлов."
            )

        return JSONResponse(content={"status": "success", "files": urls}, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображений: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при загрузке изображений")


@router.get("/list", summary="Получение списка изображений")
async def get_avatar_list(
    user: User = Depends(get_current_user)
):
    """Возвращает список URL-ов всех изображений."""
    try:
        files = os.listdir(AVATAR_DIR)
        image_urls = [
            f"{AVATAR_URL_PREFIX}/{filename}"
            for filename in files
            if filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
        ]
        return {"files": image_urls}

    except Exception as e:
        logger.error(f"Ошибка при получении списка изображений: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении списка изображений")


@router.get("/{filename}", summary="Получение URL изображения по имени файла")
async def get_avatar(
    filename: str,
    user: User = Depends(get_current_user)
):
    """Проверяет существование файла и возвращает его URL."""
    try:
        file_path = os.path.join(AVATAR_DIR, filename)

        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="Изображение не найдено")

        file_url = f"{AVATAR_URL_PREFIX}/{filename}"
        return {"url": file_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении URL изображения: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка при получении изображения")



# @router.post("/upload", summary="Загрузка нескольких аватаров")
# async def upload_avatars(
#         files: List[UploadFile] = File(...),
#         user: User = Depends(get_current_user)
# ):
#     """Загружает несколько изображений одновременно."""
#     try:
#         allowed_content_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
#         max_size = 1024 * 1024  # 1MB
#
#         successful_uploads = 0
#
#         for file in files:
#             if file.content_type not in allowed_content_types:
#                 logger.warning(f"Пропущен файл {file.filename}: неподдерживаемый тип {file.content_type}")
#                 continue
#
#             file_data = await file.read()
#
#             if len(file_data) > max_size:
#                 logger.warning(f"Пропущен файл {file.filename}: превышен размер {len(file_data)}")
#                 continue
#
#             await create_avatar(file.filename, file.content_type, file_data)
#             successful_uploads += 1
#
#         if successful_uploads == 0:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Ни один файл не был загружен. Проверьте типы и размеры файлов."
#             )
#
#         return JSONResponse(content={"status": "success"}, status_code=201)
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Ошибка при загрузке изображений: {str(e)}")
#         raise HTTPException(status_code=500, detail="Ошибка при загрузке изображений")
#
#
# @router.get("/list", summary="Получение списка изображений", response_model=AvatarListResponse)
# async def get_avatar_list(
#         user: User = Depends(get_current_user)
# ):
#     """Возвращает список всех изображений."""
#     try:
#         avatars = await get_all_avatars()
#
#         return AvatarListResponse(
#             items=[AvatarResponse.from_orm(avatar) for avatar in avatars],
#             total=len(avatars)
#         )
#     except Exception as e:
#         logger.error(f"Ошибка при получении списка изображений: {str(e)}")
#         raise HTTPException(status_code=500, detail="Ошибка при получении списка изображений")
#
#
# @router.get("/{avatar_id}", summary="Получение изображения по ID")
# async def get_avatar(
#         avatar_id: int,
#         user: User = Depends(get_current_user)
# ):
#     """Возвращает изображение по ID."""
#     try:
#         avatar = await get_avatar_by_id(avatar_id)
#
#         if not avatar:
#             raise HTTPException(status_code=404, detail="Изображение не найдено")
#
#         # Возвращаем изображение
#         return StreamingResponse(
#             content=iter([avatar.data]),
#             media_type=avatar.content_type,
#             headers={"Content-Disposition": f"inline; filename={avatar.filename}"}
#         )
#
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Ошибка при получении изображения: {str(e)}")
#         raise HTTPException(status_code=500, detail="Ошибка при получении изображения")