from fastapi import APIRouter
from fastapi import HTTPException
from loguru import logger
from starlette import status

from src import schemas
from src.core.exceptions import UserAlreadyExistsError, DatabaseOperationError
from src.repositories.user import create_new_user

router = APIRouter()


@router.post(
    "/create",
    response_model=schemas.User,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Invalid input data"},
        409: {"description": "User already exists"},
        500: {"description": "Internal server error"}
    }
)
async def create_user(user_data: schemas.UserCreate) -> schemas.User:
    """
    Create a new user endpoint.

    Args:
        user_data: Validated user creation data

    Returns:
        schemas.User: Created user data

    Raises:
        HTTPException: On various error conditions with appropriate status codes
    """
    try:
        return await create_new_user(user_data=user_data)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(e), "details": e.details}
        )
    except DatabaseOperationError as e:
        logger.error("Database error during user creation",
                     extra={"error_details": e.details})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )
    except Exception as e:
        logger.exception("Unexpected error during user creation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
