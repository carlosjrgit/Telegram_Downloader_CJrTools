import json
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from modules.logger import get_logger
from modules.utils import human_readable_size

logger = get_logger(__name__)


class Statistics:
    """Gerencia estatísticas agregadas da execução de forma thread-safe."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self._lock = threading.Lock()
        self.total_files = 0
        self.completed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.corrupted_files = 0
        self.filtered_files = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.type_counts: dict[str, int] = defaultdict(int)

    def add_file_processed(self, status: str, mime_type: str, size: int, bytes_downloaded: int = 0) -> None:
        """
        Registra um arquivo processado de forma thread-safe.

        Args:
            status: COMPLETED, FAILED, SKIPPED, CORRUPTED, FILTERED.
            mime_type: tipo MIME do arquivo.
            size: tamanho total em bytes.
            bytes_downloaded: bytes efetivamente baixados (pode ser 0 se pulado).
        """
        with self._lock:
            self.total_files += 1
            self.total_bytes += size
            if status == "COMPLETED":
                self.completed_files += 1
                self.downloaded_bytes += bytes_downloaded
            elif status == "FAILED":
                self.failed_files += 1
            elif status == "SKIPPED":
                self.skipped_files += 1
            elif status == "CORRUPTED":
                self.corrupted_files += 1
            elif status in ("FILTERED", "IGNORED_BY_FILTER"):
                self.filtered_files += 1
            self.type_counts[mime_type] += 1

    def print_summary(self) -> None:
        """Exibe o resumo final no console."""
        with self._lock:
            elapsed = time.time() - self.start_time
            avg_speed = self.downloaded_bytes / elapsed if elapsed > 0 else 0
            print("\n=== RESUMO DA SINCRONIZAÇÃO ===")
            print(f"Arquivos analisados: {self.total_files}")
            print(f"  Concluídos com sucesso: {self.completed_files}")
            print(f"  Falhas registradas:    {self.failed_files}")
            print(f"  Pulados (já íntegros): {self.skipped_files}")
            print(f"  Corrompidos/rebaixados: {self.corrupted_files}")
            print(f"  Ignorados pelo filtro:  {self.filtered_files}")
            print(f"Volume planejado: {human_readable_size(self.total_bytes)}")
            print(f"Bytes baixados nesta execução: {human_readable_size(self.downloaded_bytes)}")
            print(f"Tempo decorrido: {elapsed:.1f}s")
            print(f"Velocidade média: {human_readable_size(avg_speed)}/s")

    def save_status_report(
        self,
        txt_path: str = "logs/status_relatorio.txt",
        json_path: str = "logs/status_relatorio.json",
        db_summary: dict[str, Any] | None = None,
        entity_name: str = "Sessão Ativa"
    ) -> None:
        """Gera um relatório completo e legível do status em tempo real."""
        with self._lock:
            elapsed = time.time() - self.start_time
            avg_speed = self.downloaded_bytes / elapsed if elapsed > 0 else 0

            # Formata tempo decorrido
            mins, secs = divmod(int(elapsed), 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours}h {mins:02d}m {secs:02d}s" if hours > 0 else f"{mins}m {secs:02d}s"

            # Dados consolidados (prioriza DB se fornecido)
            total_f = db_summary.get("total_files", self.total_files) if db_summary else self.total_files
            comp_f = db_summary.get("completed_files", self.completed_files) if db_summary else self.completed_files
            fail_f = db_summary.get("failed_files", self.failed_files) if db_summary else self.failed_files
            pend_f = db_summary.get("pending_files", 0) if db_summary else (total_f - comp_f - fail_f)

            total_b = db_summary.get("total_bytes", self.total_bytes) if db_summary else self.total_bytes
            comp_b = db_summary.get("completed_bytes", self.downloaded_bytes) if db_summary else self.downloaded_bytes
            pct = (comp_b / total_b * 100) if total_b > 0 else 0

            # 1. Salva relatório em TXT legível
            Path(txt_path).parent.mkdir(parents=True, exist_ok=True)
            report_lines = [
                "=" * 70,
                f"RELATÓRIO DE STATUS DA SESSÃO: {entity_name}",
                f"Atualizado em: {time.strftime('%d/%m/%Y %H:%M:%S')}",
                f"Tempo em Execução: {time_str}",
                "=" * 70,
                "PROGRESSO DO ACERVO:",
                f"  - Total de Arquivos Alvo: {total_f:>6d}  ({human_readable_size(total_b):>10s})",
                f"  - Concluídos com Sucesso: {comp_f:>6d}  ({human_readable_size(comp_b):>10s})",
                f"  - Pendentes / Em Fila:    {pend_f:>6d}  ({human_readable_size(max(0, total_b - comp_b)):>10s})",
                f"  - Falhas Temporárias:     {fail_f:>6d}",
                f"  - Progresso Total:        {pct:>6.2f} %",
                "-" * 70,
                "DESEMPENHO DA SESSÃO ATUAL:",
                f"  - Volume Baixado nesta Execução: {human_readable_size(self.downloaded_bytes)}",
                f"  - Velocidade Média:              {human_readable_size(avg_speed)}/s",
                "=" * 70
            ]

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines) + "\n")

            # 2. Salva relatório em JSON estruturado
            json_data = {
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "entity_name": entity_name,
                "elapsed_seconds": elapsed,
                "elapsed_formatted": time_str,
                "total_files": total_f,
                "completed_files": comp_f,
                "pending_files": pend_f,
                "failed_files": fail_f,
                "total_bytes": total_b,
                "completed_bytes": comp_b,
                "progress_percentage": round(pct, 2),
                "session_downloaded_bytes": self.downloaded_bytes,
                "average_speed_bytes_sec": avg_speed,
                "average_speed_formatted": f"{human_readable_size(avg_speed)}/s"
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)

    def save_to_log(self, log_path: str) -> None:
        """Salva as estatísticas no histórico JSON acumulado."""
        with self._lock:
            elapsed = time.time() - self.start_time
            data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_files": self.total_files,
                "completed": self.completed_files,
                "failed": self.failed_files,
                "skipped": self.skipped_files,
                "corrupted": self.corrupted_files,
                "filtered": self.filtered_files,
                "total_bytes": self.total_bytes,
                "downloaded_bytes": self.downloaded_bytes,
                "elapsed_seconds": elapsed,
                "average_speed_bytes_per_sec": self.downloaded_bytes / elapsed if elapsed > 0 else 0,
                "types": dict(self.type_counts)
            }
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, indent=2) + "\n")
