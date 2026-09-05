"""
Script de automação para compilar o executável Telegram_Downloader_CJrTools.exe com PyInstaller.
Gera executável autônomo e arquivo de checksum SHA-256 para distribuição via GitHub Releases.
"""

from __future__ import annotations

import hashlib
import os
import subprocess  # nosec B404
import sys
from pathlib import Path


def compute_file_sha256(filepath: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo binário."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def build_executable() -> None:
    """Executa o PyInstaller com todas as dependências e opções necessárias."""
    print("=== Iniciando compilação do Telegram_Downloader_CJrTools.exe ===")

    dist_dir = Path("dist")
    data_sep = ";" if os.name == "nt" else ":"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=Telegram_Downloader_CJrTools",
        "--onefile",
        "--noconsole",
        "--clean",
        "--icon=gui/assets/logo.ico",
        "--collect-all=telethon",
        "--collect-all=qasync",
        "--collect-all=PyQt6",
        "--collect-all=platformdirs",
        "--hidden-import=modules",
        "--hidden-import=gui",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        f"--add-data=config.example.json{data_sep}.",
        f"--add-data=gui/assets{data_sep}gui/assets",
        "gui_main.py"
    ]

    print(f"Executando: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False)  # nosec B603

    if result.returncode != 0:
        print("\n[ERRO] Falha durante a compilação do executável com PyInstaller.")
        sys.exit(result.returncode)

    exe_name = "Telegram_Downloader_CJrTools.exe" if os.name == "nt" else "Telegram_Downloader_CJrTools"
    exe_path = dist_dir / exe_name

    if exe_path.exists():
        sha256_hash = compute_file_sha256(exe_path)
        checksum_file = dist_dir / "SHA256SUMS.txt"
        with open(checksum_file, "w", encoding="utf-8") as f:
            f.write(f"{sha256_hash}  {exe_name}\n")

        # Arquivo adicional compatível
        with open(dist_dir / "checksums_sha256.txt", "w", encoding="utf-8") as f:
            f.write(f"{sha256_hash}  {exe_name}\n")

        print("\n=======================================================")
        print(f"[OK] Executável gerado com sucesso em: '{exe_path}'")
        print(f"[OK] SHA-256: {sha256_hash}")
        print(f"[OK] Checksum salvo em: '{checksum_file}'")
        print("=======================================================\n")
    else:
        print(f"[ERRO] Arquivo {exe_path} não encontrado na pasta dist.")


if __name__ == "__main__":
    build_executable()
