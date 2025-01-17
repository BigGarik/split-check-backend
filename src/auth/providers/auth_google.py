from google.auth.transport import requests
from google.oauth2 import id_token
from loguru import logger

from src.config.settings import settings

GOOGLE_CLIENT_IDS = {
    "android": settings.google_android_client_id,
    "ios": settings.google_ios_client_id
}


class GoogleOAuth:
    """Класс для взаимодействия с Google OAuth."""
    def __init__(self, token: str, platform: str):
        self.token = token
        self.platform = platform

    def get_user_info(self):
        logger.debug("Start_get_user_info")
        client_id = GOOGLE_CLIENT_IDS[self.platform]
        # Верифицируем token от Google
        id_info = id_token.verify_oauth2_token(
            self.token,
            requests.Request(),
            client_id
        )
        print(f"id_info: {id_info}")
        # email = id_info.get('email')
        # name = id_info.get('name')
        # # locale =
        # picture = id_info.get('picture')

        return id_info


# class GoogleOAuth(OAuthProvider):
#     """Класс для взаимодействия с Google OAuth."""
#     def __init__(self, client_id: str, redirect_uri: str, client_secret: Optional[str] = None):
#         super().__init__(
#             client_id=client_id,
#             client_secret=client_secret,
#             redirect_uri=redirect_uri,
#             token_url="https://oauth2.googleapis.com/token",
#             userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
#         )
#
#     async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
#         """Обмен кода авторизации на токен доступа."""
#         data = {
#             'code': code,
#             'client_id': self.client_id,
#             'redirect_uri': self.redirect_uri,
#             'grant_type': 'authorization_code',
#         }
#         if self.client_secret:
#             data['client_secret'] = self.client_secret
#
#         headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#
#         async with httpx.AsyncClient() as client:
#             response = await client.post(self.token_url, data=data, headers=headers)
#             response.raise_for_status()
#             return response.json()
#
#     async def get_user_info(self, access_token: str) -> Dict[str, Any]:
#         """Получение информации о пользователе с использованием токена доступа."""
#         headers = {'Authorization': f'Bearer {access_token}'}
#
#         async with httpx.AsyncClient() as client:
#             response = await client.get(self.userinfo_url, headers=headers)
#             response.raise_for_status()
#             return response.json()
