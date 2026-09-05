"""
Módulo de exportação de inventário e catálogo de arquivos para CSV.
Implementa proteção contra CSV Injection (Formula Injection).
"""

import csv
from pathlib import Path
from typing import Any

from modules.utils import human_readable_size

# Caracteres que disparam execução de fórmulas em softwares de planilha
DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> Any:
    """
    Neutraliza Formula Injection em células de texto exportadas para CSV.
    Se o texto iniciar com caracteres de comando de fórmula, prefixa com apóstrofo (').
    """
    if isinstance(value, str):
        # Remove quebras de linha que possam quebrar linhas CSV
        cleaned = value.replace("\r", " ").replace("\n", " ")
        if cleaned.startswith(DANGEROUS_CSV_PREFIXES):
            return f"'{cleaned}"
        return cleaned
    return value


def export_catalog_csv(files_list: list[dict[str, Any]], target_path: str | Path) -> str:
    """
    Exporta a lista de arquivos encontrados para um arquivo CSV estruturado.
    Utiliza delimitador ';' e codificação 'utf-8-sig' para compatibilidade com o Excel.
    Aplica neutralização contra CSV Injection em todos os campos de texto.
    """
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "Numero",
            "ID_Mensagem",
            "Nome_Arquivo",
            "Extensao",
            "Tipo_MIME",
            "Tamanho_Legivel",
            "Tamanho_Bytes",
            "Data_Envio"
        ])

        for idx, item in enumerate(files_list, start=1):
            raw_size = item.get("file_size", 0)
            formatted_size = human_readable_size(raw_size) if raw_size > 0 else "Tam. dinâmico"
            writer.writerow([
                idx,
                item.get("message_id", ""),
                sanitize_csv_cell(item.get("file_name", "")),
                sanitize_csv_cell(item.get("extension", "")),
                sanitize_csv_cell(item.get("mime_type", "")),
                formatted_size,
                raw_size,
                sanitize_csv_cell(item.get("date", ""))
            ])

    return str(path.resolve())
