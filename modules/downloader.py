"""
Módulo principal de download: iteração sobre mensagens e gerenciamento de downloads concorrentes.
Implementa download atômico (.part), retomada segura (resume), verificação de espaço em disco
e proteção contra path traversal e symlink attacks.
"""

import asyncio
import errno
import os
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.errors import FileReferenceExpiredError, FloodWaitError, RPCError
from telethon.tl.types import (
    DocumentAttributeAudio,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    Message,
    MessageMediaDocument,
    MessageMediaPhoto,
)
from tqdm import tqdm

from config import Config
from modules.database import Database
from modules.exceptions import DownloadError, IntegrityError
from modules.filter import FileFilter
from modules.integrity import compute_sha256, verify_file_integrity
from modules.logger import get_logger
from modules.progress import ProgressManager
from modules.retry import async_retry
from modules.statistics import Statistics
from modules.utils import human_readable_size, safe_join, sanitize_filename

logger = get_logger(__name__)


def check_available_disk_space(target_dir: Path, required_bytes: int, safety_margin_mb: int = 100) -> bool:
    """
    Verifica se há espaço em disco suficiente no diretório de destino.
    """
    try:
        usage = shutil.disk_usage(target_dir)
        safety_bytes = safety_margin_mb * 1024 * 1024
        return usage.free >= (required_bytes + safety_bytes)
    except OSError as e:
        logger.warning(f"Não foi possível verificar o espaço em disco para '{target_dir}': {e}")
        return True


class Downloader:
    """Gerencia o processo de download de mídias de um chat com suporte a múltiplos downloads simultâneos."""

    def __init__(
        self,
        client: TelegramClient,
        entity: Any,
        output_dir: Path,
        db: Database,
        config: Config,
        stats: Statistics,
        file_filter: FileFilter | None = None
    ) -> None:
        self.client = client
        self.entity = entity
        self.output_dir = Path(output_dir).resolve()
        self.db = db
        self.config = config
        self.stats = stats
        self.file_filter = file_filter or FileFilter("ALL")
        self._flood_wait_until: float = 0.0

    def _get_entity_title(self) -> str:
        """Obtém um nome legível para a entidade (Canal, Grupo ou Usuário)."""
        return (
            getattr(self.entity, "title", None)
            or getattr(self.entity, "username", None)
            or getattr(self.entity, "first_name", None)
            or str(getattr(self.entity, "id", "chat"))
        )

    async def scan_channel(
        self,
        limit: int | None = None,
        min_date: Any | None = None,
        progress_callback: Callable[[int, int, int, int | None], None] | None = None
    ) -> dict[str, Any]:
        """
        Executa uma varredura de metadados das mensagens para listar
        todos os arquivos disponíveis e estimar o espaço total em disco.
        Exibe barra de progresso visual e notifica callback para interfaces gráficas.
        """
        entity_name = self._get_entity_title()
        logger.info(f"Iniciando escaneamento rápido de metadados para: '{entity_name}' (Limite: {limit}, Data mínima: {min_date})")

        total_channel_messages: int | None = None
        try:
            res = await self.client.get_messages(self.entity, limit=0)
            if hasattr(res, "total"):
                total_channel_messages = res.total
        except Exception as e:
            logger.debug(f"Não foi possível obter o total de mensagens previamente: {e}")

        if limit and total_channel_messages:
            scan_total = min(limit, total_channel_messages)
        elif limit:
            scan_total = limit
        else:
            scan_total = total_channel_messages

        total_messages = 0
        total_media = 0
        total_bytes = 0
        files_list = []
        type_summary: dict[str, dict[str, Any]] = {}

        scan_bar = tqdm(
            total=scan_total,
            desc="Varrendo histórico",
            unit=" msg",
            dynamic_ncols=True,
            leave=True
        )

        async for message in self.client.iter_messages(self.entity, limit=limit, reverse=True):
            total_messages += 1
            scan_bar.update(1)

            if not message or not message.media:
                if progress_callback and total_messages % 50 == 0:
                    progress_callback(total_messages, total_media, total_bytes, scan_total)
                continue

            if min_date and getattr(message, "date", None) and message.date < min_date:
                continue

            file_meta = self._extract_file_meta(message)
            if not file_meta:
                continue

            total_media += 1
            file_name = file_meta["file_name"]
            mime_type = file_meta["mime_type"]
            file_size = file_meta["file_size"]
            ext = file_meta["extension"] or "outros"

            total_bytes += file_size

            if ext not in type_summary:
                type_summary[ext] = {"count": 0, "bytes": 0}
            type_summary[ext]["count"] += 1
            type_summary[ext]["bytes"] += file_size

            files_list.append({
                "message_id": message.id,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": mime_type,
                "extension": ext,
                "date": file_meta.get("date", "")
            })

            scan_bar.set_postfix({
                "Mídias": total_media,
                "Tamanho": human_readable_size(total_bytes)
            }, refresh=False)

            if progress_callback and (total_messages % 20 == 0 or total_media % 10 == 0):
                progress_callback(total_messages, total_media, total_bytes, scan_total)

        scan_bar.close()

        if progress_callback:
            progress_callback(total_messages, total_media, total_bytes, scan_total)

        return {
            "entity_name": entity_name,
            "total_messages": total_messages,
            "total_media": total_media,
            "total_bytes": total_bytes,
            "files": files_list,
            "type_summary": type_summary
        }

    async def run(
        self,
        initial_total_bytes: int = 0,
        limit: int | None = None,
        min_date: Any | None = None,
        target_message_ids: list[int] | None = None
    ) -> None:
        """Executa o download de mídias de forma concorrente em streaming com suporte a busca direta por IDs."""
        entity_name = self._get_entity_title()
        num_workers = max(1, self.config.concurrent_downloads)
        logger.info(f"Iniciando sincronização de '{entity_name}' com {num_workers} download(s) simultâneo(s) em streaming")

        # Verifica espaço em disco disponível antes de iniciar o lote
        if initial_total_bytes > 0 and not check_available_disk_space(self.output_dir, initial_total_bytes):
            logger.warning(
                    f"Atenção: Espaço livre em disco pode ser insuficiente para o lote completo "
                    f"({human_readable_size(initial_total_bytes)} planejados)."
                )

        progress = ProgressManager(
            total_bytes=initial_total_bytes,
            desc="Progresso Geral",
            max_slots=num_workers + 1
        )

        queue: asyncio.Queue = asyncio.Queue(maxsize=50)

        # 1. Produtor: busca mensagens e alimenta a fila em tempo real
        async def producer():
            if target_message_ids is not None:
                batch_size = 100
                for i in range(0, len(target_message_ids), batch_size):
                    batch_ids = target_message_ids[i:i + batch_size]
                    try:
                        messages = await self.client.get_messages(self.entity, ids=batch_ids)
                    except Exception as e:
                        logger.error(f"Erro ao buscar lote de mensagens por ID: {e}")
                        continue

                    for message in messages:
                        if not message or not getattr(message, "media", None):
                            continue
                        file_meta = self._extract_file_meta(message)
                        if not file_meta:
                            continue
                        clean_filename = sanitize_filename(file_meta["file_name"])
                        unique_filename = f"{message.id}_{clean_filename}"
                        try:
                            local_path = safe_join(self.output_dir, unique_filename)
                        except ValueError as e:
                            logger.error(f"Arquivo ignorado por violação de caminho seguro: {e}")
                            continue
                        await queue.put((message, file_meta, local_path, unique_filename))
            else:
                async for message in self.client.iter_messages(self.entity, limit=limit, reverse=True):
                    if not message or not getattr(message, "media", None):
                        continue
                    if min_date and getattr(message, "date", None) and message.date < min_date:
                        continue
                    file_meta = self._extract_file_meta(message)
                    if not file_meta:
                        continue
                    clean_filename = sanitize_filename(file_meta["file_name"])
                    if not self.file_filter.should_download(clean_filename, file_meta["mime_type"]):
                        self.stats.add_file_processed("FILTERED", file_meta["mime_type"], file_meta["file_size"])
                        continue
                    unique_filename = f"{message.id}_{clean_filename}"
                    try:
                        local_path = safe_join(self.output_dir, unique_filename)
                    except ValueError as e:
                        logger.error(f"Arquivo ignorado por violação de caminho seguro: {e}")
                        continue
                    await queue.put((message, file_meta, local_path, unique_filename))

            for _ in range(num_workers):
                await queue.put(None)

        # 2. Consumidores (Workers concorrentes)
        async def worker(worker_id: int):
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break

                message, file_meta, local_path, unique_filename = item

                # Checagem se o arquivo final já foi baixado e está íntegro
                db_record = self.db.get_file(file_meta["message_id"], file_meta["file_id"])
                if not self.config.overwrite_existing and db_record and db_record["status"] == "COMPLETED" and local_path.exists():
                    expected_size = db_record["expected_size"] or file_meta["file_size"]
                    if self.config.verify_integrity:
                        if verify_file_integrity(local_path, expected_size, db_record.get("hash")):
                            logger.info(f"[Worker {worker_id}] Já concluído e íntegro (ignorado): {unique_filename}")
                            self.stats.add_file_processed("SKIPPED", file_meta["mime_type"], expected_size)
                            queue.task_done()
                            continue
                        else:
                            logger.warning(f"[Worker {worker_id}] Arquivo corrompido: {unique_filename}. Rebaixando...")
                            self.db.update_status(file_meta["message_id"], file_meta["file_id"], "CORRUPTED")
                    else:
                        logger.info(f"[Worker {worker_id}] Já baixado anteriormente (ignorado): {unique_filename}")
                        self.stats.add_file_processed("SKIPPED", file_meta["mime_type"], expected_size)
                        queue.task_done()
                        continue

                if not db_record:
                    self.db.upsert_file({
                        "message_id": file_meta["message_id"],
                        "file_id": file_meta["file_id"],
                        "file_name": unique_filename,
                        "file_size": file_meta["file_size"],
                        "mime_type": file_meta["mime_type"],
                        "extension": file_meta["extension"],
                        "local_path": str(local_path),
                        "status": "PENDING"
                    })

                now = time.time()
                if self._flood_wait_until > now:
                    wait_time = self._flood_wait_until - now
                    logger.warning(f"[Worker {worker_id}] Aguardando {wait_time:.1f}s devido ao FloodWait do Telegram...")
                    await asyncio.sleep(wait_time)

                try:
                    await self._download_with_retry(worker_id, message, file_meta, local_path, progress)
                except Exception as e:
                    logger.error(f"Falha no download de {unique_filename}: {e}")
                    self.db.update_status(file_meta["message_id"], file_meta["file_id"], "FAILED")
                    self.stats.add_file_processed("FAILED", file_meta["mime_type"], file_meta["file_size"])
                finally:
                    queue.task_done()

        producer_task = asyncio.create_task(producer())
        worker_tasks = [asyncio.create_task(worker(i)) for i in range(1, num_workers + 1)]

        await asyncio.gather(producer_task, *worker_tasks)
        progress.close()
        logger.info(f"Sincronização do chat '{entity_name}' finalizada.")

    def _extract_file_meta(self, message: Message) -> dict[str, Any] | None:
        """Extrai metadados do objeto Message do Telethon com mídia."""
        media = message.media
        if not media:
            return None

        date_str = message.date.strftime("%Y-%m-%d %H:%M:%S") if getattr(message, "date", None) else ""

        if isinstance(media, MessageMediaDocument) and media.document:
            doc = media.document
            file_id = str(doc.id)
            file_name = None

            for attr in doc.attributes:
                if isinstance(attr, DocumentAttributeFilename) and attr.file_name:
                    file_name = attr.file_name
                    break
                elif isinstance(attr, DocumentAttributeVideo):
                    file_name = f"video_{doc.id}.mp4"
                elif isinstance(attr, DocumentAttributeAudio):
                    file_name = f"audio_{doc.id}.mp3"

            if not file_name:
                ext = ""
                if doc.mime_type:
                    parts = doc.mime_type.split("/")
                    if len(parts) > 1:
                        ext = f".{parts[1]}"
                file_name = f"doc_{doc.id}{ext}"

            mime_type = doc.mime_type or "application/octet-stream"
            extension = Path(file_name).suffix.lower() if "." in file_name else ""

            return {
                "message_id": message.id,
                "file_id": file_id,
                "file_name": file_name,
                "file_size": doc.size,
                "mime_type": mime_type,
                "extension": extension,
                "media_obj": media,
                "date": date_str,
            }

        elif isinstance(media, MessageMediaPhoto) and media.photo:
            photo = media.photo
            file_id = str(photo.id)
            file_name = f"photo_{photo.id}.jpg"
            file_size = 0
            if hasattr(photo, "sizes") and photo.sizes:
                largest = photo.sizes[-1]
                file_size = getattr(largest, "size", 0)

            return {
                "message_id": message.id,
                "file_id": file_id,
                "file_name": file_name,
                "file_size": file_size,
                "mime_type": "image/jpeg",
                "extension": ".jpg",
                "media_obj": media,
                "date": date_str,
            }

        return None

    async def _download_with_retry(
        self,
        slot: int,
        message: Message,
        file_meta: dict[str, Any],
        local_path: Path,
        progress: ProgressManager
    ) -> None:
        """Aplica o decorador de retry em caso de falhas de rede ou FloodWait."""
        decorated = async_retry(
            max_attempts=self.config.retry_attempts,
            backoff_factor=2.0,
            exceptions=(ConnectionError, asyncio.TimeoutError, FloodWaitError, RPCError, OSError, IOError),
            log_attempts=True
        )(self._do_download)
        await decorated(slot, message, file_meta, local_path, progress)

    async def _do_download(
        self,
        slot: int,
        message: Message,
        file_meta: dict[str, Any],
        local_path: Path,
        progress: ProgressManager
    ) -> None:
        """
        Executa o download via streaming de chunks para arquivo temporário (.part).
        Garante atomicidade, suporte a retomada (resume) e verificação rigorosa de integridade.
        """
        message_id = file_meta["message_id"]
        file_id = file_meta["file_id"]
        expected_size = file_meta["file_size"]
        file_name = local_path.name
        part_path = Path(str(local_path) + ".part")

        # Retomada segura baseada no arquivo .part existente
        offset = 0
        if self.config.auto_resume and part_path.exists():
            current_part_size = part_path.stat().st_size
            if expected_size > 0 and current_part_size < expected_size:
                offset = current_part_size
                logger.info(f"[Worker {slot}] Retomando '{file_name}' a partir do byte {offset} ({human_readable_size(offset)})")
            elif expected_size > 0 and current_part_size >= expected_size:
                offset = 0
                part_path.unlink(missing_ok=True)
            else:
                offset = current_part_size

        self.db.update_status(message_id, file_id, "DOWNLOADING")
        progress.start_file(slot, file_name, expected_size if expected_size > 0 else None)
        if offset > 0:
            progress.update_file(slot, offset, expected_size if expected_size > 0 else None)

        bytes_written_this_session = 0
        total_downloaded = offset
        last_db_update = offset

        async def _stream_chunks(media_to_download, start_offset):
            nonlocal bytes_written_this_session, total_downloaded, last_db_update
            current_mode = "ab" if start_offset > 0 else "wb"
            try:
                with open(part_path, current_mode) as f:
                    async for chunk in self.client.iter_download(
                        media_to_download,
                        offset=start_offset,
                        chunk_size=self.config.chunk_size,
                        request_size=self.config.chunk_size
                    ):
                        f.write(chunk)
                        chunk_len = len(chunk)
                        bytes_written_this_session += chunk_len
                        total_downloaded += chunk_len

                        progress.update_file(slot, total_downloaded, expected_size if expected_size > 0 else total_downloaded)

                        # Persiste progresso no SQLite a cada 1 MB
                        if total_downloaded - last_db_update >= 1024 * 1024:
                            self.db.update_progress(message_id, file_id, total_downloaded)
                            last_db_update = total_downloaded
            except OSError as os_err:
                if os_err.errno == errno.ENOSPC or "no space left" in str(os_err).lower():
                    logger.error(f"[Worker {slot}] Espaço em disco esgotado (ENOSPC) ao gravar '{file_name}'!")
                    raise DownloadError(f"Espaço em disco esgotado ao gravar {file_name}") from os_err
                raise

        try:
            try:
                await _stream_chunks(message.media, offset)
            except (FileReferenceExpiredError, RPCError, Exception) as stream_err:
                if isinstance(stream_err, FileReferenceExpiredError) or "file reference has expired" in str(stream_err).lower():
                    logger.warning(f"[Worker {slot}] Token expirado para '{file_name}'. Renovando file_reference com o Telegram...")
                    refreshed = await self.client.get_messages(self.entity, ids=message_id)
                    if refreshed and getattr(refreshed, "media", None):
                        message.media = refreshed.media
                        file_meta["media_obj"] = refreshed.media
                        current_offset = part_path.stat().st_size if part_path.exists() else 0
                        logger.info(f"[Worker {slot}] Token renovado com sucesso para '{file_name}'! Retomando a partir do byte {current_offset} ({human_readable_size(current_offset)})")
                        await _stream_chunks(message.media, current_offset)
                    else:
                        raise stream_err
                else:
                    raise stream_err

            # 1. Validação de tamanho no arquivo temporário .part
            final_size = part_path.stat().st_size
            if expected_size == 0 and final_size > 0:
                expected_size = final_size
                self.db.conn.execute(
                    "UPDATE files SET file_size = ?, expected_size = ? WHERE message_id = ? AND file_id = ?",
                    (final_size, final_size, message_id, file_id)
                )
                self.db.conn.commit()

            # 2. Verificação de integridade pós-download no .part
            if self.config.verify_integrity and not verify_file_integrity(part_path, expected_size):
                part_path.unlink(missing_ok=True)
                self.db.update_progress(message_id, file_id, 0)
                raise IntegrityError(f"Tamanho divergente para {file_name}")

            # 3. Cálculo de hash no .part
            hash_value = None
            if self.config.save_hash:
                hash_value = compute_sha256(part_path)

            # 4. Finalização atômica: substitui .part pelo arquivo final
            os.replace(part_path, local_path)

            self.db.update_status(message_id, file_id, "COMPLETED", hash_value)
            self.db.update_progress(message_id, file_id, final_size)

            self.stats.add_file_processed("COMPLETED", file_meta["mime_type"], final_size, bytes_written_this_session)
            progress.update_global(bytes_written_this_session)
            logger.info(f"[Worker {slot}] Concluído com sucesso: {file_name} ({human_readable_size(final_size)})")

            # Atualiza relatório de status em tempo real
            self.stats.save_status_report(
                db_summary=self.db.get_summary_counts(),
                entity_name=self._get_entity_title()
            )

        except FloodWaitError as e:
            self._flood_wait_until = time.time() + e.seconds + 1.0
            raise
        except Exception as e:
            if isinstance(e, IntegrityError):
                raise
            if part_path.exists():
                self.db.update_progress(message_id, file_id, part_path.stat().st_size)
            raise
        finally:
            progress.finish_file(slot)
