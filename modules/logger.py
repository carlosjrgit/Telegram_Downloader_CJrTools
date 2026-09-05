"""
Configuração e obtenção de loggers para o projeto.
Implementa rotação automática de logs (RotatingFileHandler) e filtro contra Log Injection.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from modules.utils import sanitize_log_text


class SafeFormatter(logging.Formatter):
    """Formatter defensivo que neutraliza caracteres de controle e CRLF das mensagens de log."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, str):
            record.msg = sanitize_log_text(record.msg)
        return super().format(record)


def setup_logging(logs_dir: str | Path = "logs", log_level: str = "INFO") -> None:
    """
    Configura os handlers de log com rotação automática de arquivos e formatação segura.

    Args:
        logs_dir: diretório onde os arquivos de log serão gravados.
        log_level: nível do logger raiz (DEBUG, INFO, WARNING, etc.).
    """
    log_path = Path(logs_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = SafeFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    # 1. Handler com rotação para download.log (10 MB por arquivo, até 5 backups)
    download_handler = RotatingFileHandler(
        log_path / "download.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    download_handler.setLevel(logging.DEBUG)
    download_handler.setFormatter(formatter)
    root_logger.addHandler(download_handler)

    # 2. Handler com rotação para errors.log (apenas WARNING+)
    error_handler = RotatingFileHandler(
        log_path / "errors.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 3. Handler para console (INFO+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Reduz verbosidade excessiva de bibliotecas de terceiros
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retorna um logger configurado com o nome especificado."""
    return logging.getLogger(name)
