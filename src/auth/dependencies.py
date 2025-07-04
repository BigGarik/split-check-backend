import logging

from fastapi import HTTPException
from firebase_admin import auth

from src.config import config

logger = logging.getLogger(config.app.service_name)


def get_firebase_user(id_token):
    """Get the user details from Firebase, based on TokenID in the request

    :param id_token: id_token
    """
    logger.debug(f"id_token: {id_token}")
    if not id_token:
        raise HTTPException(status_code=400, detail='TokenID must be provided')

    try:
        claims = auth.verify_id_token(id_token)
        return claims
    except Exception as e:
        logger.debug(e)
        raise HTTPException(status_code=401, detail='Unauthorized')
