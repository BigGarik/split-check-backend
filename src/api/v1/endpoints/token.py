from typing import Dict

from fastapi import APIRouter, Depends, status, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError

from src.config.settings import settings
from src.core.security import verify_token
from src.services.auth import authenticate_user, generate_tokens
from src.schemas import RefreshTokenRequest, TokenResponse


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# Эндпоинт для получения access_token и refresh_token
@router.post(
    "",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Incorrect username or password"},
        429: {"description": "Too many login attempts"},
    }
)
async def login_for_access_token(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends()
) -> Dict[str, str]:
    """Login endpoint to obtain access and refresh tokens."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await generate_tokens(user.email, user.id)

    # Установить refresh token в HTTP-only cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,  # для HTTPS
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60
    )

    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"description": "Invalid refresh token"}
    }
)
async def refresh_access_token(request: RefreshTokenRequest) -> Dict[str, str]:
    """Refresh access token using either cookie or request body."""
    token = request.refresh_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is missing"
        )

    try:
        email, user_id = await verify_token(
            secret_key=settings.refresh_secret_key,
            token=token
        )
        tokens = await generate_tokens(email, user_id)

        return tokens
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(response: Response):
    """Clear refresh token cookie."""
    response.delete_cookie(
        key="refresh_token",
        secure=True,
        httponly=True
    )
    return {"message": "Successfully logged out"}
