"""
Criação e configuração do cliente Telethon com armazenamento seguro de sessões.
"""

from telethon import TelegramClient

from config import Config
from modules.paths import get_session_dir


def get_telegram_client(config: Config) -> TelegramClient:
    """
    Retorna uma instância do TelegramClient configurada com a sessão persistente
    em local seguro da conta do usuário.

    Args:
        config: objeto de configuração contendo api_id, api_hash e phone.

    Returns:
        Cliente Telethon pronto para uso.
    """
    session_dir = get_session_dir()
    phone_clean = config.phone.replace("+", "").strip() if config.phone else "default_session"
    session_file = session_dir / phone_clean

    client = TelegramClient(str(session_file), config.api_id, config.api_hash)
    return client
