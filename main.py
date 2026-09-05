"""
Ponto de entrada do Telegram_Downloader_CJrTools.
Orquestra o fluxo completo: configuração, autenticação, seleção de origem,
destino, e início da sincronização de arquivos.
Suporta execução via CLI tradicional ou Interface Gráfica moderna (--gui).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import Config, ConfigError
from modules.database import Database
from modules.downloader import Downloader
from modules.export import export_catalog_csv
from modules.file_manager import ensure_directory
from modules.filter import FileFilter
from modules.logger import get_logger, setup_logging
from modules.paths import get_config_path, get_database_path, get_log_dir
from modules.statistics import Statistics
from modules.telegram_client import get_telegram_client
from modules.utils import human_readable_size, sanitize_filename, sanitize_input

logger = get_logger(__name__)


def run_wizard(config: Config) -> None:
    """Executa o assistente interativo de primeira configuração para obter API_ID, API_HASH e Telefone."""
    print("\n=== Configuração inicial da API do Telegram ===\n")
    if not config.api_id:
        while True:
            raw_id = sanitize_input("Digite seu API_ID: ").strip()
            if raw_id.isdigit():
                config.api_id = int(raw_id)
                break
            print("API_ID deve ser um número inteiro positivo válido.")
    if not config.api_hash:
        while True:
            raw_hash = sanitize_input("Digite seu API_HASH: ").strip()
            if raw_hash:
                config.api_hash = raw_hash
                break
            print("API_HASH não pode ser vazio.")
    if not config.phone:
        while True:
            raw_phone = sanitize_input("Digite seu número de telefone com DDI e DDD (ex: +5511999999999): ").strip()
            if raw_phone:
                config.phone = raw_phone
                break
            print("Número de telefone não pode ser vazio.")
    config.save()
    print(f"[✓] Configurações salvas com sucesso em: '{config.filepath}'\n")


def select_scan_scope() -> tuple[int | None, datetime | None]:
    """Menu para definir o escopo de varredura (histórico completo, limite ou período)."""
    print(f"\n{'=' * 15} ESCOPO DA VARREDURA {'=' * 15}")
    print("[1] Histórico Completo (Todo o canal/grupo)")
    print("[2] Limitar por Quantidade de Mensagens Recentes (ex: últimas 500, 1000)")
    print("[3] Limitar por Período Recente (ex: últimos 30 dias, 6 meses, etc.)")
    print("=" * 55)

    choice = sanitize_input("Escolha o escopo [1]: ").strip()

    if choice == "2":
        while True:
            raw = sanitize_input("Quantas mensagens recentes deseja verificar? (ex: 500): ").strip()
            if raw.isdigit() and int(raw) > 0:
                return int(raw), None
            print("Por favor, digite um número inteiro positivo.")

    elif choice == "3":
        while True:
            raw = sanitize_input("Quantos dias recentes deseja verificar? (ex: 30, 90, 365): ").strip()
            if raw.isdigit() and int(raw) > 0:
                days = int(raw)
                min_dt = datetime.now(timezone.utc) - timedelta(days=days)
                return None, min_dt
            print("Por favor, digite um número de dias válido.")

    return None, None


def print_files_compactly(files: list, max_display: int = 30) -> None:
    """Exibe os arquivos de forma limpa no console, utilizando amostragem se a lista for grande."""
    total = len(files)
    print(f"\n{'=' * 15} ARQUIVOS IDENTIFICADOS NO CHAT ({total}) {'=' * 15}")

    if total <= max_display:
        for idx, f in enumerate(files, start=1):
            size_str = human_readable_size(f["file_size"]) if f["file_size"] > 0 else "Tam. dinâmico"
            print(f"[{idx:4d}] {f['file_name'][:62]:<62} ({size_str:>10s})")
    else:
        for idx in range(1, 11):
            f = files[idx - 1]
            size_str = human_readable_size(f["file_size"]) if f["file_size"] > 0 else "Tam. dinâmico"
            print(f"[{idx:4d}] {f['file_name'][:62]:<62} ({size_str:>10s})")

        print(f"\n    ... [ {total - 20} arquivos intermediários omitidos no console ] ...\n")

        for idx in range(total - 9, total + 1):
            f = files[idx - 1]
            size_str = human_readable_size(f["file_size"]) if f["file_size"] > 0 else "Tam. dinâmico"
            print(f"[{idx:4d}] {f['file_name'][:62]:<62} ({size_str:>10s})")

    print("=" * 80)


def configure_filters_interactively(scanned_files: list) -> FileFilter | None:
    """Menu interativo para filtragem após visualização da lista de arquivos."""
    print(f"\n{'=' * 15} OPÇÕES DE DOWNLOAD {'=' * 15}")
    print("[1] Baixar TODOS os arquivos listados acima")
    print("[2] Filtrar por Palavras-Chave (Incluir / Ignorar)")
    print("[3] Cancelar operação")
    print("=" * 55)

    choice = sanitize_input("Escolha uma opção [1]: ").strip()
    if choice == "3":
        return None
    if choice != "2":
        return FileFilter(mode="ALL")

    print("\n--- Filtro de Inclusão (Whitelist) ---")
    print("Digite os termos/extensões que DEVEM estar no nome do arquivo (separados por vírgula).")
    print("Exemplos: Aula, Modulo 01, .mp4, Python")
    inc_raw = sanitize_input("Termos para INCLUIR (ou Enter para todos): ").strip()
    include_terms = [t.strip() for t in inc_raw.split(",") if t.strip()] if inc_raw else []

    print("\n--- Filtro de Exclusão (Blacklist) ---")
    print("Digite os termos/extensões que NÃO devem ser baixados (separados por vírgula).")
    print("Exemplos: Gabarito, Anuncio, .zip, Exercicio")
    exc_raw = sanitize_input("Termos para IGNORAR/EXCLUIR (ou Enter para nenhum): ").strip()
    exclude_terms = [t.strip() for t in exc_raw.split(",") if t.strip()] if exc_raw else []

    file_filter = FileFilter(mode="CUSTOM", include_terms=include_terms, exclude_terms=exclude_terms)

    matching = [f for f in scanned_files if file_filter.should_download(f["file_name"], f.get("mime_type", ""))]
    matching_bytes = sum(f["file_size"] for f in matching)

    print(f"\n{'=' * 15} PRÉVIA DOS ARQUIVOS FILTRADOS {'=' * 15}")
    print(f"Arquivos selecionados: {len(matching)} de {len(scanned_files)}")
    print(f"Arquivos descartados:  {len(scanned_files) - len(matching)}")
    print(f"Espaço total a baixar: {human_readable_size(matching_bytes)}")

    if matching:
        print("\nArquivos que serão baixados:")
        print_files_compactly(matching, max_display=20)

    return file_filter


async def select_target_dialog(client: Any) -> Any:
    """Recupera e lista todos os grupos e canais da conta para seleção por número."""
    print("\nBuscando grupos e canais disponíveis na sua conta do Telegram...")
    dialogs = []
    async for dialog in client.iter_dialogs():
        if dialog.is_group or dialog.is_channel:
            dialogs.append(dialog)

    if not dialogs:
        print("\nNenhum grupo ou canal foi encontrado na sua conta do Telegram.")
        sys.exit(0)

    print(f"\n{'=' * 15} GRUPOS E CANAIS DISPONÍVEIS ({len(dialogs)}) {'=' * 15}")
    for idx, d in enumerate(dialogs, start=1):
        tipo = "Canal" if d.is_channel and not d.is_group else "Grupo"
        name = d.name if d.name else "Sem título"
        print(f"[{idx:3d}] {name}  [{tipo}]")

    print("=" * 55)

    while True:
        choice = sanitize_input(f"\nDigite o número do grupo/canal desejado (1 a {len(dialogs)}): ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(dialogs):
                selected = dialogs[idx - 1]
                print(f"\nSelecionado: {selected.name} (ID: {selected.id})")
                return selected.entity
        print(f"Opção inválida! Digite um número válido entre 1 e {len(dialogs)}.")


async def async_main() -> None:
    """Função principal assíncrona com ciclo de vida unificado."""
    logs_dir = get_log_dir()
    setup_logging(logs_dir=logs_dir, log_level="INFO")
    logger.info("Iniciando Telegram_Downloader_CJrTools")

    config_path = get_config_path()
    config = Config(config_path)
    try:
        config.load()
    except ConfigError as ce:
        logger.error(f"Erro na configuração: {ce}")
        print(f"\n[ERRO DE CONFIGURAÇÃO] {ce}")
        sys.exit(1)
    except FileNotFoundError:
        logger.info(f"Criando arquivo de configuração padrão em: {config_path}")
        config.save()

    if not config.api_id or not config.api_hash or not config.phone:
        run_wizard(config)

    db_path = get_database_path()
    db = Database(db_path)
    db.initialize()

    client = get_telegram_client(config)
    stats = Statistics()

    try:
        await client.start(phone=config.phone)
        logger.info("Autenticado com sucesso no Telegram.")

        session_info = db.get_session_info()
        pending_files = db.get_pending_files()

        resumed_session = False
        if session_info and pending_files:
            summary = db.get_summary_counts()
            completed_f = summary.get("completed_files", 0)
            pending_f = len(pending_files)
            dest_dir = Path(session_info["dest_path"])

            print(f"\n{'=' * 20} SESSÃO ANTERIOR IDENTIFICADA {'=' * 20}")
            print(f"Chat / Canal:        {session_info['entity_title']}")
            print(f"Pasta de Destino:    {dest_dir}")
            print(f"Arquivos Concluídos: {completed_f}")
            print(f"Arquivos Pendentes:  {pending_f} ({human_readable_size(sum(f['file_size'] for f in pending_files))})")
            print("=" * 68)
            print("[1] RETOMAR DOWNLOADS PENDENTES IMEDIATAMENTE (Pula varredura e filtros, baixa na hora)")
            print("[2] Iniciar nova varredura / novos filtros")
            print("=" * 68)

            choice = sanitize_input("Escolha uma opção [1]: ").strip()
            if choice != "2":
                resumed_session = True
                entity_id_raw = session_info["entity_id"]
                try:
                    entity_id = int(entity_id_raw)
                except ValueError:
                    entity_id = entity_id_raw

                print(f"\nConectando ao chat '{session_info['entity_title']}' para retomada imediata...")
                entity = await client.get_entity(entity_id)
                downloader = Downloader(client, entity, dest_dir, db, config, stats)

                target_ids = [f["message_id"] for f in pending_files]
                total_bytes_to_download = sum(f["file_size"] for f in pending_files)

                print(f"\nIniciando download dos {len(pending_files)} arquivo(s) pendentes ({human_readable_size(total_bytes_to_download)})...")
                await downloader.run(
                    initial_total_bytes=total_bytes_to_download,
                    target_message_ids=target_ids
                )

        if not resumed_session:
            # 1. Seleciona grupo/canal numerado
            entity = await select_target_dialog(client)
            entity_title = (
                getattr(entity, "title", None)
                or getattr(entity, "username", None)
                or getattr(entity, "first_name", None)
                or str(getattr(entity, "id", "chat"))
            )

            # 2. Diretório de destino
            default_path = Path(config.download_path)
            dest = sanitize_input(f"\nOnde deseja salvar os arquivos? [{default_path}]: ").strip()
            if not dest:
                dest = str(default_path)
            dest_path = Path(dest).expanduser().resolve()

            if not dest_path.exists():
                resp = sanitize_input(f"A pasta '{dest_path}' não existe. Deseja criar? [Y/N]: ").strip().lower()
                if resp != "y":
                    print("Operação cancelada pelo usuário.")
                    return
                ensure_directory(dest_path)

            # 3. Verifica se já existem arquivos registrados para retomar antes de escanear
            pending_files_channel = db.get_pending_files()
            summary_db = db.get_summary_counts()
            completed_count = summary_db.get("completed_files", 0)

            should_rescan = True
            if pending_files_channel:
                total_pending = len(pending_files_channel)
                bytes_pending = sum(f["file_size"] for f in pending_files_channel)

                print(f"\n{'=' * 20} ARQUIVOS JÁ REGISTRADOS NO BANCO {'=' * 20}")
                print(f"Chat / Canal:        {entity_title}")
                print(f"Pasta de Destino:    {dest_path}")
                print(f"Arquivos Concluídos: {completed_count} ({human_readable_size(summary_db.get('completed_bytes', 0))})")
                print(f"Arquivos a Baixar:   {total_pending} ({human_readable_size(bytes_pending)})")
                print("=" * 68)
                print("[1] RETOMAR DOWNLOADS PENDENTES IMEDIATAMENTE (Pula varredura e filtros, baixa na hora)")
                print("[2] Fazer nova varredura e redefinir filtros")
                print("=" * 68)

                opt = sanitize_input("Escolha uma opção [1]: ").strip()
                if opt != "2":
                    should_rescan = False
                    db.save_session_info(entity.id, entity_title, str(dest_path))
                    downloader = Downloader(client, entity, dest_path, db, config, stats)
                    target_ids = [f["message_id"] for f in pending_files_channel]

                    print(f"\nIniciando download dos {total_pending} arquivo(s) pendentes ({human_readable_size(bytes_pending)})...")
                    await downloader.run(
                        initial_total_bytes=bytes_pending,
                        target_message_ids=target_ids
                    )

            if should_rescan:
                limit_count, min_date = select_scan_scope()

                downloader = Downloader(client, entity, dest_path, db, config, stats)

                print("\nAnalisando metadados e indexando arquivos disponíveis...")
                scan_result = await downloader.scan_channel(limit=limit_count, min_date=min_date)
                files = scan_result.get("files", [])

                if not files:
                    print("\nNenhum arquivo ou mídia foi encontrado no escopo selecionado.")
                    return

                # Exportação do catálogo para CSV com nome seguro no diretório de logs
                safe_title = sanitize_filename(entity_title)
                csv_filename = f"catalogo_{safe_title}.csv"
                csv_path = logs_dir / csv_filename
                exported_file = export_catalog_csv(files, csv_path)

                print_files_compactly(files, max_display=30)
                print(f"Total de arquivos: {len(files)} | Espaço Total Estimado: {human_readable_size(scan_result['total_bytes'])}")
                print(f"Catálogo completo exportado para planilha CSV: '{exported_file}'")
                print("=" * 80)

                file_filter = configure_filters_interactively(files)
                if file_filter is None:
                    print("\nOperação cancelada pelo usuário.")
                    return

                downloader.file_filter = file_filter

                filtered_files = [f for f in files if file_filter.should_download(f["file_name"], f.get("mime_type", ""))]
                if not filtered_files:
                    print("\nNenhum arquivo corresponde aos critérios de filtro configurados.")
                    return

                total_bytes_to_download = sum(f["file_size"] for f in filtered_files)

                confirm = sanitize_input(f"\nIniciar download de {len(filtered_files)} arquivo(s) ({human_readable_size(total_bytes_to_download)})? [Y/N]: ").strip().lower()
                if confirm != "y":
                    print("\nDownload cancelado pelo usuário.")
                    return

                db.save_session_info(entity.id, entity_title, str(dest_path))

                target_ids = [f["message_id"] for f in filtered_files]
                await downloader.run(
                    initial_total_bytes=total_bytes_to_download,
                    limit=limit_count,
                    min_date=min_date,
                    target_message_ids=target_ids
                )

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Execução interrompida pelo usuário. Os downloads parciais serão retomados na próxima execução.")
    except Exception as e:
        logger.exception(f"Erro na execução: {e}")
    finally:
        db_summary = db.get_summary_counts()
        entity_name_for_report = downloader._get_entity_title() if "downloader" in locals() else "Sessão"
        status_txt = logs_dir / "status_relatorio.txt"
        status_json = logs_dir / "status_relatorio.json"
        stats.save_status_report(
            txt_path=str(status_txt),
            json_path=str(status_json),
            db_summary=db_summary,
            entity_name=entity_name_for_report
        )
        db.close()
        stats.print_summary()
        stats.save_to_log(str(logs_dir / "statistics.log"))
        print(f"\n[✓] Relatório detalhado salvo em: '{status_txt}'")
        if client.is_connected():
            await client.disconnect()
        logger.info("Cliente desconectado e recursos liberados.")

    print("\nPrograma finalizado.")


def main() -> None:
    """Ponto de entrada do programa (CLI ou GUI)."""
    if "--gui" in sys.argv or "-g" in sys.argv:
        try:
            from gui.app import run_gui
            run_gui()
            return
        except ImportError as e:
            print(f"[AVISO] Não foi possível iniciar a interface gráfica: {e}")
            print("Certifique-se de instalar os requisitos da GUI: pip install PyQt6 qasync")
            sys.exit(1)

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nPrograma finalizado pelo usuário.")


if __name__ == "__main__":
    main()
