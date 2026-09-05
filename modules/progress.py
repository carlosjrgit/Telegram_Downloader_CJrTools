"""
Gerenciamento das barras de progresso (individual multi-slot e global).
"""

import contextlib
import threading
import time

from tqdm import tqdm


class ProgressManager:
    """Controla as barras de progresso com tqdm com suporte a downloads concorrentes."""

    def __init__(self, total_bytes: int, desc: str = "Progresso Geral", max_slots: int = 5) -> None:
        self.total_bytes = total_bytes
        self.downloaded_global = 0
        self.start_time = time.time()
        self._lock = threading.Lock()
        self.max_slots = max_slots
        self._file_bars: dict[int, tqdm] = {}

        self.global_bar = tqdm(
            total=total_bytes if total_bytes > 0 else None,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=desc,
            position=0,
            leave=True,
            dynamic_ncols=True
        )

    def start_file(self, slot: int, file_name: str, file_size: int | None = None) -> None:
        """
        Inicia uma barra de progresso no slot atribuído ao worker.

        Args:
            slot: número da posição da barra no terminal (1 a N).
            file_name: nome do arquivo.
            file_size: tamanho total em bytes (ou None se desconhecido).
        """
        with self._lock:
            if slot in self._file_bars:
                with contextlib.suppress(Exception):
                    self._file_bars[slot].close()

            total = file_size if file_size and file_size > 0 else None
            clean_desc = file_name[:32]
            self._file_bars[slot] = tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=f"[Slot {slot}] {clean_desc}",
                position=slot,
                leave=False,
                dynamic_ncols=True
            )

    def update_file(self, slot: int, current: int, total: int | None = None) -> None:
        """
        Atualiza a barra do slot com os bytes já baixados.

        Args:
            slot: posição do worker.
            current: bytes baixados até o momento.
            total: tamanho total atualizado (se descoberto durante o stream).
        """
        with self._lock:
            bar = self._file_bars.get(slot)
            if bar:
                if total and (bar.total is None or bar.total == 0):
                    bar.total = total
                bar.n = current
                bar.refresh()

    def finish_file(self, slot: int) -> None:
        """Finaliza e limpa a barra do slot do worker."""
        with self._lock:
            if slot in self._file_bars:
                with contextlib.suppress(Exception):
                    self._file_bars[slot].clear()
                    self._file_bars[slot].close()
                del self._file_bars[slot]

    def update_global(self, increment: int) -> None:
        """
        Incrementa o progresso global acumulado de todos os downloads.

        Args:
            increment: bytes adicionais baixados.
        """
        with self._lock:
            self.downloaded_global += increment
            self.global_bar.n = self.downloaded_global
            self.global_bar.refresh()

    def close(self) -> None:
        """Fecha com segurança todas as barras ativas."""
        with self._lock:
            for bar in list(self._file_bars.values()):
                with contextlib.suppress(Exception):
                    bar.clear()
                    bar.close()
            self._file_bars.clear()
            with contextlib.suppress(Exception):
                self.global_bar.close()

    def elapsed_time(self) -> float:
        """Retorna o tempo decorrido em segundos."""
        return time.time() - self.start_time

    def average_speed(self) -> float:
        """Retorna a velocidade média em bytes/s."""
        elapsed = self.elapsed_time()
        if elapsed > 0:
            return self.downloaded_global / elapsed
        return 0.0
