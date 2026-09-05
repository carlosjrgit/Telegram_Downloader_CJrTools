"""
Funções utilitárias: sanitização de nomes de arquivos, proteção contra path traversal,
formatação de tamanhos e neutralização de injeção em logs.
"""

import os
import re
import unicodedata
from pathlib import Path

# Nomes de dispositivos reservados no Windows (case-insensitive)
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# Caracteres estritamente proibidos no Windows: \ / : * ? " < > | e caracteres de controle 0-31
INVALID_FILENAME_CHARS = r'[\\/*?:"<>|\x00-\x1f\x7f-\x9f]'
MAX_FILENAME_LENGTH = 180


def sanitize_filename(filename: str, max_length: int = MAX_FILENAME_LENGTH) -> str:
    """
    Higieniza rigorosamente um nome de arquivo recebido do Telegram.
    Remove path traversal, caracteres proibidos no Windows, quebras de linha e nomes reservados.

    Args:
        filename: nome original vindo da rede/metadados.
        max_length: limite máximo de caracteres no nome do arquivo.

    Returns:
        Nome seguro para salvar no disco.
    """
    if not filename:
        return "unnamed_file"

    # 1. Remove componentes de diretório e path traversal (../ ou ..\)
    filename = os.path.basename(filename.replace("\\", "/"))

    # 2. Substitui caracteres inválidos e de controle por underline
    sanitized = re.sub(INVALID_FILENAME_CHARS, "_", filename)

    # 3. Remove categorias de controle Unicode (Cc, Cf, Cs, Co, Cn)
    sanitized = "".join(ch for ch in sanitized if unicodedata.category(ch)[0] not in ("C",))

    # 4. Remove espaços extras e pontos no final/início que Windows não aceita
    sanitized = sanitized.strip(". ")

    if not sanitized:
        sanitized = "unnamed_file"

    # 5. Verifica se o stem do arquivo é um nome reservado do Windows
    stem = Path(sanitized).stem.upper()
    ext = Path(sanitized).suffix
    if stem in WINDOWS_RESERVED_NAMES:
        sanitized = f"safe_{sanitized}"

    # 6. Limitação de tamanho preservando a extensão
    if len(sanitized) > max_length:
        if ext and len(ext) < max_length:
            stem_allowed = max_length - len(ext)
            sanitized = sanitized[:stem_allowed].rstrip(". ") + ext
        else:
            sanitized = sanitized[:max_length].rstrip(". ")

    return sanitized if sanitized else "unnamed_file"


def safe_join(base_dir: str | Path, untrusted_path: str | Path) -> Path:
    """
    Combina um diretório base confiável com um caminho não confiável,
    garantindo que o caminho resultante não escape do diretório base (Path Traversal).

    Args:
        base_dir: diretório base autorizado.
        untrusted_path: caminho relativo ou filename não confiável.

    Returns:
        Path canônico e seguro dentro de base_dir.

    Raises:
        ValueError: se houver tentativa de escape de diretório.
    """
    base = Path(base_dir).resolve()
    # Se untrusted_path for absoluto, usa apenas a parte do nome/relativa segura
    clean_untrusted = Path(untrusted_path)
    if clean_untrusted.is_absolute():
        clean_untrusted = Path(*clean_untrusted.parts[1:])

    candidate = (base / clean_untrusted).resolve()

    # Validação rigorosa de escape de diretório
    try:
        candidate.relative_to(base)
    except ValueError:
        raise ValueError(
            f"Tentativa de Path Traversal detectada: '{untrusted_path}' "
            f"tenta escapar de '{base}'."
        ) from None

    return candidate


def sanitize_log_text(text: str) -> str:
    """
    Neutraliza quebras de linha e caracteres de controle para evitar Log Injection (CRLF).
    """
    if not text:
        return ""
    # Substitui quebras de linha e retornos de carro por espaços
    clean = text.replace("\r", " ").replace("\n", " ")
    # Remove outros caracteres de controle
    return "".join(ch for ch in clean if unicodedata.category(ch)[0] != "C")


def human_readable_size(size_bytes: int | float) -> str:
    """Converte bytes em string legível (ex: 1.25 MB)."""
    if size_bytes <= 0:
        return "0 B"
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.2f} PB"


def sanitize_input(prompt: str) -> str:
    """Captura entrada do usuário no console com tratamento de cancelamento."""
    try:
        return input(prompt)
    except (EOFError, KeyboardInterrupt):
        print("\nOperação cancelada pelo usuário.")
        raise
