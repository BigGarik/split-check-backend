import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import aiohttp

from src.config import OPEN_EXCHANGE_RATES_API_KEY
from src.redis import redis_client

logger = logging.getLogger(__name__)

api_key = OPEN_EXCHANGE_RATES_API_KEY
cache_key = "exchange_rates"


async def cache_rates_to_midnight(rates: dict):
    """
    Сохраняет курсы обмена в Redis с истечением в полночь UTC.

    Args:
        rates (dict): Словарь с курсами обмена
    """
    # Текущее время в UTC
    now = datetime.now(timezone.utc)

    # Время до полуночи UTC
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    expire_seconds = int((midnight - now).total_seconds())

    # Сохранение в Redis с истечением в полночь
    await redis_client.set(cache_key, json.dumps(rates), expire=expire_seconds)
    logger.info(f"Курсы обмена сохранены в Redis с истечением в {midnight}")


async def get_exchange_rates() -> Optional[dict]:
    url = f"https://openexchangerates.org/api/latest.json?app_id={api_key}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                rates = data.get("rates", {})

                await cache_rates_to_midnight(rates)

                return rates

    except Exception as e:
        logger.exception(e)
        return None


async def get_exchange_rate(from_currency: str, to_currency: str) -> Optional[float]:
    """
    Получает курс обмена между двумя валютами с использованием Open Exchange Rates API.

    Args:
        from_currency (str): Исходная валюта (например, "USD")
        to_currency (str): Целевая валюта (например, "EUR")

    Returns:
        Optional[float]: Курс обмена или None, если курс недоступен
    """
    try:
        rates = await redis_client.get(cache_key)
        if rates:
            rates = json.loads(rates)
        else:
            rates = await get_exchange_rates()
            if not rates:
                return None
        exchange_rate = rates.get(from_currency) / rates.get(to_currency)
        return exchange_rate

    except Exception as e:
        logger.exception(e)
        return None


