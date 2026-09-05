"""
Exceções personalizadas para o projeto.
"""

class DownloadError(Exception):
    """Erro geral durante o download."""

class IntegrityError(Exception):
    """Falha na verificação de integridade do arquivo baixado."""

class AuthenticationError(Exception):
    """Erro relacionado à autenticação com o Telegram."""

class ConfigError(Exception):
    """Erro de configuração (faltando campos obrigatórios, etc.)."""
