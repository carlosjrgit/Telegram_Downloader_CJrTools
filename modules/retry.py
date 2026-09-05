"""
Decorador para retry automático com backoff exponencial.
"""

import asyncio
import functools
from collections.abc import Callable

from telethon.errors import FloodWaitError

from modules.logger import get_logger

logger = get_logger(__name__)


def async_retry(
    max_attempts: int = 5,
    backoff_factor: float = 2.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    log_attempts: bool = True
):
    """
    Decorador para funções assíncronas que tenta novamente em caso de exceção.

    Args:
        max_attempts: número máximo de tentativas.
        backoff_factor: fator multiplicador do intervalo entre tentativas.
        exceptions: tupla de exceções que disparam retry.
        log_attempts: se deve logar as tentativas.

    Returns:
        Decorador configurado.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    wait = e.seconds if isinstance(e, FloodWaitError) else backoff_factor ** attempt
                    if log_attempts:
                        logger.warning(
                            f"Tentativa {attempt}/{max_attempts} falhou: {e}. "
                            f"Aguardando {wait:.1f}s antes de tentar novamente."
                        )
                    await asyncio.sleep(wait)
            logger.error(f"Todas as {max_attempts} tentativas falharam. Último erro: {last_exception}")
            raise last_exception
        return wrapper
    return decorator
