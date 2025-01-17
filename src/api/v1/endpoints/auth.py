import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from loguru import logger
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from src.repositories.user import get_user_by_email, create_new_user
from src.schemas import UserCreate

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
templates = Jinja2Templates(directory="templates")


@router.get("/test", response_class=HTMLResponse)
async def serve_html(request: Request):
    return templates.TemplateResponse("google_auth.html", {"request": request})


@router.post("/auth/callback")
async def auth_callback(id_token):
    """
    Обрабатывает OAuth авторизацию для мобильных приложений (Google, другие провайдеры).
    """
    try:
        claims = auth.verify_id_token(id_token)
        email = claims.get('email')
        logger.debug(f"user: {claims}")

        user = await get_user_by_email(email)
        if not user:
            # Создаем нового пользователя
            user = await create_new_user(
                user_data=UserCreate(
                    email=email,
                    password=uuid.uuid4().hex
                ),
                profile_data={
                    "nickname": claims.get("name"),
                    "avatar_url": claims.get('picture')
                }
            )
        #
        # # Генерируем токены для пользователя
        # tokens = await generate_tokens(email=user.email, user_id=user.id)
        return {"user_id": user.id}

    except ValueError as e:
        # Ошибка верификации токена
        logger.error(f"Invalid token: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid token"
        )
    except Exception as e:
        # Логируем неожиданные ошибки
        logger.error(f"Unexpected error during Google authentication: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )

# @router.get("/callback")
# async def google_auth_callback(
#     code: str = Query(..., description="Authorization code от Google"),
# ):
#     """
#     Обрабатывает callback от Google OAuth2 и создает пользователя,
#     если его нет в базе. Также заполняет профиль пользователя.
#
#     Args:
#         code (str): Authorization code от Google.
#         session (AsyncSession): Асинхронная сессия базы данных.
#
#     Returns:
#         dict: Токены доступа и обновления.
#     """
#     # try:
#     # Получаем access token и данные пользователя от Google
#     logger.debug(f"Authorization code от Google: {code}")
#     access_token = await google_oauth.get_access_token(code)
#
#     # Получение данных пользователя
#     user_info = await google_oauth.get_user_info(access_token)
#     logger.debug(f"User info: {user_info}")
#
#     email = user_info.get("email")
#     if not email:
#         raise HTTPException(status_code=400, detail="Email not provided by Google")
#
#     # Проверяем, существует ли пользователь
#     user = await get_user_by_email(email)
#     if not user:
#         # Создаем нового пользователя
#         user = await create_new_user(
#             user_data=UserCreate(
#                 email=email,
#                 password=uuid.uuid4().hex
#             ),
#             profile_data={
#                 "nickname": user_info.get("name"),
#                 "avatar_url": user_info.get("picture")
#             }
#         )
#
#     # Генерируем токены для пользователя
#     tokens = await generate_tokens(email=user.email, user_id=user.id)
#     return tokens

# except Exception as e:
#     raise HTTPException(status_code=500, detail=f"Authorization failed: {str(e)}")
