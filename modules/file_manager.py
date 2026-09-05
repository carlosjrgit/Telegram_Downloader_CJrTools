"""
Gerenciamento de diretórios e caminhos de arquivos.
"""

from pathlib import Path


def ensure_directory(path: str | Path) -> None:
    """
    Cria o diretório se não existir.

    Args:
        path: caminho do diretório.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
