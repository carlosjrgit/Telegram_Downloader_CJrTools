"""
Gerenciamento do banco de dados SQLite para controle de downloads.
Garante consultas parametrizadas contra SQL Injection, concorrência WAL e permissões seguras.
"""

import contextlib
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from modules.logger import get_logger

logger = get_logger(__name__)


class Database:
    """Encapsula acesso ao banco de dados de metadados dos arquivos de forma thread-safe."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL;")  # Desempenho e concorrência
        self.conn.row_factory = sqlite3.Row

        # Restringe permissões do arquivo em POSIX
        if os.name != "nt" and self.db_path.exists():
            with contextlib.suppress(OSError):
                os.chmod(self.db_path, 0o600)

    def initialize(self) -> None:
        """Cria as tabelas do banco de dados se não existirem."""
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    message_id INTEGER,
                    file_id TEXT,
                    file_name TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    extension TEXT,
                    local_path TEXT,
                    downloaded_bytes INTEGER DEFAULT 0,
                    expected_size INTEGER,
                    status TEXT DEFAULT 'PENDING',
                    hash TEXT,
                    download_date TEXT,
                    last_update TEXT,
                    PRIMARY KEY (message_id, file_id)
                );
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS session_info (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    entity_id TEXT,
                    entity_title TEXT,
                    dest_path TEXT,
                    last_active TEXT
                );
            """)
            self.conn.commit()
            logger.info("Banco de dados inicializado com sucesso.")

    def save_session_info(self, entity_id: Any, entity_title: str, dest_path: str) -> None:
        """Salva as informações da sessão ativa para permitir retomada rápida."""
        with self._lock:
            self.conn.execute("""
                INSERT INTO session_info (id, entity_id, entity_title, dest_path, last_active)
                VALUES (1, ?, ?, ?, datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    entity_id=excluded.entity_id,
                    entity_title=excluded.entity_title,
                    dest_path=excluded.dest_path,
                    last_active=datetime('now');
            """, (str(entity_id), str(entity_title), str(dest_path)))
            self.conn.commit()

    def get_session_info(self) -> dict[str, Any] | None:
        """Recupera as informações da última sessão ativa."""
        with self._lock:
            cur = self.conn.execute("SELECT * FROM session_info WHERE id = 1")
            row = cur.fetchone()
            return dict(row) if row else None

    def get_pending_files(self) -> list[dict[str, Any]]:
        """Retorna todos os arquivos que ainda não foram concluídos."""
        with self._lock:
            cur = self.conn.execute(
                "SELECT * FROM files WHERE status != 'COMPLETED' ORDER BY message_id ASC"
            )
            return [dict(row) for row in cur.fetchall()]

    def get_summary_counts(self) -> dict[str, Any]:
        """Retorna resumo quantitativo de status e tamanhos do banco de dados."""
        with self._lock:
            cur = self.conn.execute("""
                SELECT
                    COUNT(*) as total_files,
                    SUM(file_size) as total_bytes,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_files,
                    SUM(CASE WHEN status = 'COMPLETED' THEN file_size ELSE 0 END) as completed_bytes,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed_files,
                    SUM(CASE WHEN status NOT IN ('COMPLETED', 'FAILED') THEN 1 ELSE 0 END) as pending_files,
                    SUM(downloaded_bytes) as total_downloaded_bytes
                FROM files;
            """)
            row = cur.fetchone()
            if not row or row["total_files"] == 0:
                return {
                    "total_files": 0, "total_bytes": 0,
                    "completed_files": 0, "completed_bytes": 0,
                    "failed_files": 0, "pending_files": 0,
                    "total_downloaded_bytes": 0
                }
            return dict(row)

    def upsert_file(self, data: dict[str, Any]) -> None:
        """
        Insere ou atualiza um registro de arquivo usando consultas parametrizadas.
        """
        with self._lock:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO files
                    (message_id, file_id, file_name, file_size, mime_type, extension,
                     local_path, downloaded_bytes, expected_size, status, hash, download_date, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, datetime('now'), datetime('now'))
                ON CONFLICT(message_id, file_id) DO UPDATE SET
                    file_name=excluded.file_name,
                    file_size=excluded.file_size,
                    mime_type=excluded.mime_type,
                    extension=excluded.extension,
                    local_path=excluded.local_path,
                    expected_size=excluded.expected_size,
                    last_update=datetime('now')
            """, (
                data["message_id"], str(data["file_id"]), data["file_name"], data["file_size"],
                data["mime_type"], data["extension"], str(data["local_path"]),
                data["file_size"], data.get("status", "PENDING"), data.get("hash")
            ))
            self.conn.commit()

    def update_progress(self, message_id: int, file_id: str, downloaded_bytes: int) -> None:
        """Atualiza os bytes já baixados e a data da última atualização."""
        with self._lock:
            self.conn.execute("""
                UPDATE files SET downloaded_bytes = ?, last_update = datetime('now')
                WHERE message_id = ? AND file_id = ?
            """, (downloaded_bytes, message_id, str(file_id)))
            self.conn.commit()

    def update_status(self, message_id: int, file_id: str, status: str, hash_value: str | None = None) -> None:
        """Atualiza o status e, opcionalmente, o hash do arquivo."""
        with self._lock:
            if hash_value:
                self.conn.execute("""
                    UPDATE files SET status = ?, hash = ?, last_update = datetime('now')
                    WHERE message_id = ? AND file_id = ?
                """, (status, hash_value, message_id, str(file_id)))
            else:
                self.conn.execute("""
                    UPDATE files SET status = ?, last_update = datetime('now')
                    WHERE message_id = ? AND file_id = ?
                """, (status, message_id, str(file_id)))
            self.conn.commit()

    def get_file(self, message_id: int, file_id: str) -> dict[str, Any] | None:
        """Busca um arquivo pelo identificador composto."""
        with self._lock:
            cur = self.conn.execute(
                "SELECT * FROM files WHERE message_id = ? AND file_id = ?",
                (message_id, str(file_id))
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_all_files(self) -> list[dict[str, Any]]:
        """Retorna todos os registros do banco."""
        with self._lock:
            cur = self.conn.execute("SELECT * FROM files ORDER BY message_id")
            return [dict(row) for row in cur.fetchall()]

    def close(self) -> None:
        """Fecha a conexão com o banco de dados."""
        with self._lock, contextlib.suppress(Exception):
            self.conn.close()
