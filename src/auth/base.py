from typing import Dict, Optional
import httpx
from fastapi import HTTPException


class OAuthProvider:
    """Базовый класс для работы с OAuth-провайдерами."""
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, token_url: str, userinfo_url: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.token_url = token_url
        self.userinfo_url = userinfo_url

    async def get_access_token(self, code: str) -> str:
        """Обмен кода авторизации на access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch access token")
            return response.json().get("access_token")

    async def get_user_info(self, access_token: str) -> Dict[str, str]:
        """Получение данных пользователя."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")
            return response.json()
