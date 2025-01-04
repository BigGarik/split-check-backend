from src.auth.base import OAuthProvider


class GoogleOAuth(OAuthProvider):
    """Класс для взаимодействия с Google OAuth."""
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        super().__init__(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
        )
