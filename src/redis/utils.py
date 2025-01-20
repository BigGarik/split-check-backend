from starlette.exceptions import HTTPException
from starlette.requests import Request
from loguru import logger
from src.redis import redis_client

import jwt


async def get_token_from_redis(request: Request):
    """
    Get uid from JWT token and save claims to Redis
    """
    try:
        # Get token from headers
        token = request.headers.get('Authorization')
        if not token:
            raise HTTPException(status_code=400, detail='Token must be provided')

        # Remove 'Bearer ' if present
        token = token.replace('Bearer ', '')

        # Decode JWT without verification to get uid
        decoded = jwt.decode(token, options={"verify_signature": False})
        uid = decoded.get('uid')

        if not uid:
            raise HTTPException(status_code=400, detail='Invalid token format')

        token_data = await redis_client.get(f"token:{uid}")
        if not token_data:
            return None
        return token_data

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail='Invalid token')
    except Exception as e:
        logger.exception(e)
        raise HTTPException(status_code=401, detail='Unauthorized')
