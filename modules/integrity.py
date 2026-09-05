"""
Verificação de integridade de arquivos baixados.
"""

import hashlib
from pathlib import Path

from modules.logger import get_logger

logger = get_logger(__name__)


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Calcula o hash SHA-256 de um arquivo.

    Args:
        file_path: caminho do arquivo.
        chunk_size: tamanho do bloco de leitura.

    Returns:
        String hexadecimal do hash.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def verify_file_integrity(file_path: Path, expected_size: int, expected_hash: str | None = None) -> bool:
    """
    Verifica se o arquivo está íntegro (tamanho e, opcionalmente, hash).

    Args:
        file_path: caminho do arquivo.
        expected_size: tamanho esperado em bytes.
        expected_hash: hash SHA-256 esperado (se disponível).

    Returns:
        True se o arquivo está íntegro, False caso contrário.
    """
    if not file_path.exists():
        logger.warning(f"Arquivo não encontrado: {file_path}")
        return False

    actual_size = file_path.stat().st_size
    if expected_size > 0 and actual_size != expected_size:
        logger.warning(
            f"Tamanho divergente para {file_path.name}: "
            f"esperado {expected_size}, obtido {actual_size}"
        )
        return False
    elif expected_size == 0 and actual_size == 0:
        logger.warning(f"Arquivo vazio baixado: {file_path.name}")
        return False

    if expected_hash:
        actual_hash = compute_sha256(file_path)
        if actual_hash != expected_hash:
            logger.warning(f"Hash divergente para {file_path.name}")
            return False

    return True
