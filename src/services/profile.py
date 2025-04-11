from src.repositories.profile import get_user_profile_db, create_user_profile_db, update_user_profile_db


async def get_user_profile(user_id: int):
    return await get_user_profile_db(user_id)


async def create_user_profile(user_id: int, profile_data):
    return await create_user_profile_db(user_id, profile_data)


async def update_user_profile(user_id: int, profile_data):
    return await update_user_profile_db(user_id, profile_data)
