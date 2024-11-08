from typing import Optional


class UserCreationError(Exception):
    """Base exception for user creation errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class UserAlreadyExistsError(UserCreationError):
    """Raised when attempting to create a user with existing email."""
    pass


class DatabaseOperationError(UserCreationError):
    """Raised when database operation fails."""
    pass
