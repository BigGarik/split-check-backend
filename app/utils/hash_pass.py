import bcrypt
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Создаем пул потоков для выполнения блокирующих операций
executor = ThreadPoolExecutor()


# Функция для выполнения хеширования в пуле потоков
async def async_hash_password(password: str) -> str:
    loop = asyncio.get_running_loop()
    hashed = await loop.run_in_executor(executor, bcrypt.hashpw, password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


# Функция для выполнения проверки пароля
async def async_verify_password(password: str, hashed_password: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, bcrypt.checkpw, password.encode('utf-8'),
                                      hashed_password.encode('utf-8'))
