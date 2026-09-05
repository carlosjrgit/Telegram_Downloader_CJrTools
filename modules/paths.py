"""
Gerenciamento centralizado de caminhos da aplicação (App Data, Logs, Banco e Sessões).
Implementa suporte multiplataforma via platformdirs com fallback transparente para instalações legadas.
"""

import contextlib
import os
import sys
from pathlib import Path

APP_NAME = "Telegram_Downloader_CJrTools"
APP_AUTHOR = "CJRDOOM"


def _get_base_app_data_dir() -> Path:
    """Retorna o diretório base para dados do aplicativo na conta do usuário."""
    try:
        import platformdirs
        return Path(platformdirs.user_data_dir(appname=APP_NAME, appauthor=APP_AUTHOR))
    except ImportError:
        # Fallback padrão multiplataforma
        if sys.platform == "win32":
            local_app = os.environ.get("LOCALAPPDATA")
            if local_app:
                return Path(local_app) / APP_NAME
            return Path.home() / "AppData" / "Local" / APP_NAME
        elif sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / APP_NAME
        else:
            xdg = os.environ.get("XDG_DATA_HOME")
            if xdg:
                return Path(xdg) / APP_NAME
            return Path.home() / ".local" / "share" / APP_NAME


def get_app_data_dir() -> Path:
    """Retorna e garante a existência do diretório de dados da aplicação."""
    path = _get_base_app_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path(custom_path: str | None = None) -> Path:
    """
    Retorna o caminho do arquivo config.json.
    Prioridade:
    1. custom_path especificado
    2. config.json local existente (compatibilidade com instalações existentes)
    3. config.json no diretório de AppData do usuário
    """
    if custom_path:
        return Path(custom_path)

    local_config = Path("config.json")
    if local_config.exists():
        return local_config.resolve()

    return get_app_data_dir() / "config.json"


def get_database_path(custom_path: str | None = None) -> Path:
    """
    Retorna o caminho do arquivo SQLite de controle de downloads.
    Prioriza arquivo local existente para preservar dados de instalações anteriores.
    """
    if custom_path:
        return Path(custom_path)

    local_db = Path("downloads.db")
    if local_db.exists():
        return local_db.resolve()

    return get_app_data_dir() / "downloads.db"


def get_session_dir(custom_path: str | None = None) -> Path:
    """
    Retorna o diretório seguro para armazenamento das sessões do Telethon (.session).
    Aplica permissões restritivas (0700) em sistemas POSIX.
    """
    if custom_path:
        p = Path(custom_path)
    else:
        local_session = Path("session")
        if local_session.exists() and any(local_session.iterdir()):
            p = local_session.resolve()
        else:
            p = get_app_data_dir() / "session"

    p.mkdir(parents=True, exist_ok=True)

    # Aplica permissões restritivas se POSIX
    if os.name != "nt":
        with contextlib.suppress(OSError):
            os.chmod(p, 0o700)

    return p


def get_log_dir(custom_path: str | None = None) -> Path:
    """Retorna o diretório de logs."""
    if custom_path:
        p = Path(custom_path)
    else:
        local_logs = Path("logs")
        p = local_logs.resolve() if local_logs.exists() else get_app_data_dir() / "logs"

    p.mkdir(parents=True, exist_ok=True)
    return p
