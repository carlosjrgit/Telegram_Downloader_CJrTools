"""
Sistema de filtros para seleção e descarte de arquivos com base no nome e palavras-chave.
Suporta normalização Unicode completa (ignorando acentos e maiúsculas/minúsculas).
"""

import unicodedata


def normalize_text(text: str) -> str:
    """
    Remove acentos/diacríticos e converte o texto para minúsculas.
    Exemplo: 'Mônica' -> 'monica', 'Introdução' -> 'introducao'.
    """
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    unaccented = "".join(c for c in nfkd if not unicodedata.combining(c))
    return unaccented.lower().strip()


class FileFilter:
    """Gerencia regras de inclusão (whitelist), exclusão (blacklist) e modo ALL."""

    def __init__(
        self,
        mode: str = "ALL",
        include_terms: list[str] | None = None,
        exclude_terms: list[str] | None = None
    ) -> None:
        self.mode = (mode or "ALL").upper()
        # Normaliza todos os termos de filtro (sem acentos e em minúsculas)
        self.include_terms = [normalize_text(t) for t in (include_terms or []) if t.strip()]
        self.exclude_terms = [normalize_text(t) for t in (exclude_terms or []) if t.strip()]

    def should_download(self, file_name: str, mime_type: str = "") -> bool:
        """
        Verifica se um arquivo atende às regras de filtro.
        """
        if self.mode == "ALL" and not self.include_terms and not self.exclude_terms:
            return True

        # Normaliza o texto alvo (nome do arquivo e tipo mime)
        target_str = normalize_text(f"{file_name} {mime_type}")

        # 1. Regra de Exclusão (Blacklist): se contiver termo proibido, descarta de imediato
        if self.exclude_terms:
            for ex in self.exclude_terms:
                if ex in target_str:
                    return False

        # 2. Regra de Inclusão (Whitelist): se houver lista, deve conter pelo menos um termo
        if self.include_terms:
            matches_include = any(inc in target_str for inc in self.include_terms)
            if not matches_include:
                return False

        return True

    def summary(self) -> str:
        """Retorna uma descrição legível dos filtros ativos."""
        if self.mode == "ALL" and not self.include_terms and not self.exclude_terms:
            return "Baixar TUDO (sem restrições)"

        parts = []
        if self.include_terms:
            parts.append(f"Incluir: {self.include_terms}")
        else:
            parts.append("Incluir: Todos")

        if self.exclude_terms:
            parts.append(f"Ignorar: {self.exclude_terms}")
        else:
            parts.append("Ignorar: Nenhum")

        return " | ".join(parts)
