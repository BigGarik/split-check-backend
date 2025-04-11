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


class BaseApplicationError(Exception):
    """Базовый класс для ошибок приложения"""
    pass


class CacheError(BaseApplicationError):
    """Ошибка при работе с кешем"""
    pass


class CheckOperationError(BaseApplicationError):
    """Базовый класс для ошибок операций с чеками"""
    pass


class CheckNotFoundError(CheckOperationError):
    """Ошибка: чек не найден"""
    pass


class ItemNotFoundError(CheckOperationError):
    """Ошибка: элемент не найден в чеке"""
    pass
