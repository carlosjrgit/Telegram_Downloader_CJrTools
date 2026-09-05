"""
Gerencia o arquivo de configuração (JSON) com todas as opções do programa,
suporte a variáveis de ambiente e validação rigorosa de integridade e tipos.
"""

import contextlib
import json
import os
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Exceção levantada quando há erro na estrutura ou validação de configuração."""
    pass


class Config:
    """Representa as configurações carregadas de config.json ou variáveis de ambiente."""

    # Limites operacionais de segurança
    MIN_CHUNK_SIZE = 64 * 1024       # 64 KB
    MAX_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB
    MIN_CONCURRENT = 1
    MAX_CONCURRENT = 20
    MIN_RETRIES = 1
    MAX_RETRIES = 30
    VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        self.api_id: int | None = None
        self.api_hash: str | None = None
        self.phone: str | None = None
        self.download_path: str = "./output"
        self.chunk_size: int = 512 * 1024  # 512 KB (tamanho ótimo MTProto)
        self.concurrent_downloads: int = 3
        self.retry_attempts: int = 5
        self.verify_integrity: bool = True
        self.save_hash: bool = True
        self.overwrite_existing: bool = False
        self.auto_resume: bool = True
        self.log_level: str = "INFO"

    def _parse_bool(self, value: Any, field_name: str) -> bool:
        """Converte com segurança valores booleanos evitando que strings truthy como 'false' virem True."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            val_clean = value.strip().lower()
            if val_clean in ("true", "1", "yes", "sim", "t"):
                return True
            if val_clean in ("false", "0", "no", "nao", "não", "f"):
                return False
        if isinstance(value, (int, float)):
            return bool(value)
        raise ConfigError(f"Valor inválido para o campo booleano '{field_name}': {value!r}")

    def load(self) -> None:
        """Carrega as configurações do disco e sobrepõe com variáveis de ambiente se disponíveis."""
        data: dict[str, Any] = {}
        if self.filepath.exists():
            try:
                with open(self.filepath, encoding="utf-8") as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                raise ConfigError(f"Arquivo de configuração JSON corrompido ({self.filepath}): {e}") from e
            except OSError as e:
                raise ConfigError(f"Não foi possível ler o arquivo de configuração ({self.filepath}): {e}") from e

        # 1. Carrega do JSON
        if "api_id" in data and data["api_id"] is not None:
            try:
                self.api_id = int(data["api_id"])
            except (ValueError, TypeError):
                raise ConfigError(f"Campo 'api_id' deve ser um número inteiro, obtido: {data['api_id']!r}") from None

        self.api_hash = str(data["api_hash"]).strip() if data.get("api_hash") else None
        self.phone = str(data["phone"]).strip() if data.get("phone") else None

        if "download_path" in data and data["download_path"]:
            self.download_path = str(data["download_path"]).strip()

        if "chunk_size" in data:
            try:
                self.chunk_size = int(data["chunk_size"])
            except (ValueError, TypeError):
                raise ConfigError(f"Campo 'chunk_size' deve ser numérico, obtido: {data['chunk_size']!r}") from None

        if "concurrent_downloads" in data:
            try:
                self.concurrent_downloads = int(data["concurrent_downloads"])
            except (ValueError, TypeError):
                raise ConfigError(f"Campo 'concurrent_downloads' deve ser numérico, obtido: {data['concurrent_downloads']!r}") from None

        if "retry_attempts" in data:
            try:
                self.retry_attempts = int(data["retry_attempts"])
            except (ValueError, TypeError):
                raise ConfigError(f"Campo 'retry_attempts' deve ser numérico, obtido: {data['retry_attempts']!r}") from None

        if "verify_integrity" in data:
            self.verify_integrity = self._parse_bool(data["verify_integrity"], "verify_integrity")

        if "save_hash" in data:
            self.save_hash = self._parse_bool(data["save_hash"], "save_hash")

        if "overwrite_existing" in data:
            self.overwrite_existing = self._parse_bool(data["overwrite_existing"], "overwrite_existing")

        if "auto_resume" in data:
            self.auto_resume = self._parse_bool(data["auto_resume"], "auto_resume")

        if "log_level" in data and data["log_level"]:
            self.log_level = str(data["log_level"]).strip().upper()

        # 2. Variáveis de ambiente têm precedência sobre o arquivo local
        env_api_id = os.environ.get("TELEGRAM_API_ID")
        if env_api_id:
            try:
                self.api_id = int(env_api_id.strip())
            except ValueError:
                raise ConfigError(f"Variável de ambiente TELEGRAM_API_ID deve ser um número inteiro, obtido: {env_api_id!r}") from None

        env_api_hash = os.environ.get("TELEGRAM_API_HASH")
        if env_api_hash:
            self.api_hash = env_api_hash.strip()

        env_phone = os.environ.get("TELEGRAM_PHONE")
        if env_phone:
            self.phone = env_phone.strip()

        self.validate()

    def validate(self) -> None:
        """Valida os intervalos e restrições de cada opção de configuração."""
        if self.api_id is not None and self.api_id <= 0:
            raise ConfigError(f"O 'api_id' deve ser um número positivo maior que zero. Recebido: {self.api_id}")

        if not (self.MIN_CHUNK_SIZE <= self.chunk_size <= self.MAX_CHUNK_SIZE):
            raise ConfigError(
                f"O 'chunk_size' ({self.chunk_size} bytes) deve estar entre "
                f"{self.MIN_CHUNK_SIZE} bytes (64 KB) e {self.MAX_CHUNK_SIZE} bytes (10 MB)."
            )

        if not (self.MIN_CONCURRENT <= self.concurrent_downloads <= self.MAX_CONCURRENT):
            raise ConfigError(
                f"O 'concurrent_downloads' ({self.concurrent_downloads}) deve estar entre "
                f"{self.MIN_CONCURRENT} e {self.MAX_CONCURRENT}."
            )

        if not (self.MIN_RETRIES <= self.retry_attempts <= self.MAX_RETRIES):
            raise ConfigError(
                f"O 'retry_attempts' ({self.retry_attempts}) deve estar entre "
                f"{self.MIN_RETRIES} e {self.MAX_RETRIES}."
            )

        if self.log_level not in self.VALID_LOG_LEVELS:
            raise ConfigError(
                f"Nível de log 'log_level' inválido: '{self.log_level}'. "
                f"Opções aceitas: {', '.join(sorted(self.VALID_LOG_LEVELS))}"
            )

        if not self.download_path:
            raise ConfigError("O campo 'download_path' não pode ser vazio.")

    def save(self) -> None:
        """Persiste as configurações atuais no disco com permissões seguras."""
        self.validate()
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "phone": self.phone,
            "download_path": self.download_path,
            "chunk_size": self.chunk_size,
            "concurrent_downloads": self.concurrent_downloads,
            "retry_attempts": self.retry_attempts,
            "verify_integrity": self.verify_integrity,
            "save_hash": self.save_hash,
            "overwrite_existing": self.overwrite_existing,
            "auto_resume": self.auto_resume,
            "log_level": self.log_level
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Restringe permissões em sistemas POSIX
        if os.name != "nt":
            with contextlib.suppress(OSError):
                os.chmod(self.filepath, 0o600)
