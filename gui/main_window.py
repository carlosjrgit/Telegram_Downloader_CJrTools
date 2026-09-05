"""
Janela Principal da Interface Gráfica PyQt6.
Integra configuração, autenticação, seleção de canais, catálogo de mídias e monitoramento de downloads.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import Config
from gui.styles import (
    COLOR_ACCENT,
    COLOR_BORDER_SUBTLE,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_SURFACE_ACTIVE,
    COLOR_TEXT_SECONDARY,
    COLOR_WARNING,
)
from modules.database import Database
from modules.downloader import Downloader
from modules.export import export_catalog_csv
from modules.logger import get_logger
from modules.paths import get_config_path, get_database_path, get_log_dir
from modules.statistics import Statistics
from modules.telegram_client import get_telegram_client
from modules.utils import human_readable_size, sanitize_filename

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """Janela principal do TelegramDownloader com abas interativas e suporte assíncrono."""

    # Sinais para comunicação segura entre tarefas assíncronas e a thread da UI
    log_received = pyqtSignal(str)
    scan_progress_signal = pyqtSignal(int, int, int, int)  # total_msg, total_media, total_bytes, scan_total

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Telegram_Downloader_CJrTools")
        self.resize(1100, 750)
        self.setMinimumSize(900, 620)

        # Configurar ícone da aplicação
        icon_path = Path(__file__).parent / "assets" / "logo.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.config_path = get_config_path()
        self.config = Config(self.config_path)
        try:
            self.config.load()
        except Exception as exc:
            logger.debug("Configuração inicial não carregada: %s", exc)

        self.db = Database(get_database_path())
        self.db.initialize()
        self.stats = Statistics()

        self.client: Any | None = None
        self.current_entity: Any | None = None
        self.scanned_files: list[dict[str, Any]] = []
        self.download_task: asyncio.Task | None = None
        self.scan_task: asyncio.Task | None = None
        self.is_downloading = False
        self.is_scanning = False

        self._init_ui()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header Card
        header = QFrame()
        header.setObjectName("HeaderCard")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 4, 8, 4)

        title_box = QVBoxLayout()
        title_label = QLabel("Telegram_Downloader_CJrTools")
        title_label.setObjectName("TitleLabel")
        subtitle_label = QLabel("Download modular, seguro e resiliente de arquivos e mídias do Telegram")
        subtitle_label.setObjectName("SubtitleLabel")
        title_box.addWidget(title_label)
        title_box.addWidget(subtitle_label)
        h_layout.addLayout(title_box)

        h_layout.addStretch()

        self.status_badge = QLabel("Desconectado")
        self.status_badge.setObjectName("StatusBadgeInactive")
        h_layout.addWidget(self.status_badge)

        main_layout.addWidget(header)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tab_config = QWidget()
        self.tab_channels = QWidget()
        self.tab_catalog = QWidget()
        self.tab_downloads = QWidget()
        self.tab_about = QWidget()

        self._setup_config_tab()
        self._setup_channels_tab()
        self._setup_catalog_tab()
        self._setup_downloads_tab()
        self._setup_about_tab()

        icons_dir = Path(__file__).parent / "assets" / "icons"
        self.tabs.addTab(self.tab_config, QIcon(str(icons_dir / "gear.svg")), "Configuração")
        self.tabs.addTab(self.tab_channels, QIcon(str(icons_dir / "chats.svg")), "Canais e Grupos")
        self.tabs.addTab(self.tab_catalog, QIcon(str(icons_dir / "list-dashes.svg")), "Catálogo e Filtros")
        self.tabs.addTab(self.tab_downloads, QIcon(str(icons_dir / "download-simple.svg")), "Downloads")
        self.tabs.addTab(self.tab_about, QIcon(str(icons_dir / "info.svg")), "Sobre")

        main_layout.addWidget(self.tabs)

        self.log_received.connect(self._append_log)
        self.scan_progress_signal.connect(self._on_scan_progress)

    def _setup_config_tab(self) -> None:
        layout = QVBoxLayout(self.tab_config)
        card = QFrame()
        card.setObjectName("ContentCard")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        # API ID
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("API ID:"))
        self.input_api_id = QLineEdit()
        self.input_api_id.setPlaceholderText("Ex: 12345678")
        if self.config.api_id:
            self.input_api_id.setText(str(self.config.api_id))
        h1.addWidget(self.input_api_id)
        c_layout.addLayout(h1)

        # API Hash
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("API Hash:"))
        self.input_api_hash = QLineEdit()
        self.input_api_hash.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_hash.setPlaceholderText("Ex: 0123456789abcdef0123456789abcdef")
        if self.config.api_hash:
            self.input_api_hash.setText(str(self.config.api_hash))
        h2.addWidget(self.input_api_hash)
        c_layout.addLayout(h2)

        # Telefone
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Telefone:"))
        self.input_phone = QLineEdit()
        self.input_phone.setPlaceholderText("Ex: +5511999999999")
        if self.config.phone:
            self.input_phone.setText(str(self.config.phone))
        h3.addWidget(self.input_phone)
        c_layout.addLayout(h3)

        # Pasta de Download
        h4 = QHBoxLayout()
        h4.addWidget(QLabel("Pasta de Download:"))
        self.input_dest = QLineEdit()
        self.input_dest.setText(str(Path(self.config.download_path).resolve()))
        h4.addWidget(self.input_dest)

        btn_browse = QPushButton("Procurar...")
        btn_browse.setObjectName("SecondaryButton")
        btn_browse.clicked.connect(self._browse_dest_dir)
        h4.addWidget(btn_browse)
        c_layout.addLayout(h4)

        # Opções Operacionais
        h5 = QHBoxLayout()
        h5.addWidget(QLabel("Downloads Concorrentes:"))
        self.spin_concurrent = QSpinBox()
        self.spin_concurrent.setRange(1, 10)
        self.spin_concurrent.setValue(self.config.concurrent_downloads)
        h5.addWidget(self.spin_concurrent)

        self.chk_integrity = QCheckBox("Verificar Integridade")
        self.chk_integrity.setChecked(self.config.verify_integrity)
        h5.addWidget(self.chk_integrity)

        self.chk_hash = QCheckBox("Salvar SHA-256 no Banco")
        self.chk_hash.setChecked(self.config.save_hash)
        h5.addWidget(self.chk_hash)
        c_layout.addLayout(h5)

        icons_dir = Path(__file__).parent / "assets" / "icons"

        # Botões de Ação
        btn_layout = QHBoxLayout()
        self.btn_save_config = QPushButton("Salvar Configurações")
        self.btn_save_config.setObjectName("SecondaryButton")
        self.btn_save_config.setIcon(QIcon(str(icons_dir / "check-circle.svg")))
        self.btn_save_config.clicked.connect(self._save_config)
        btn_layout.addWidget(self.btn_save_config)

        self.btn_connect = QPushButton("Conectar ao Telegram")
        self.btn_connect.setObjectName("SuccessButton")
        self.btn_connect.setIcon(QIcon(str(icons_dir / "play.svg")))
        self.btn_connect.clicked.connect(self._on_connect_clicked)
        btn_layout.addWidget(self.btn_connect)

        c_layout.addLayout(btn_layout)
        layout.addWidget(card)
        layout.addStretch()

    def _setup_channels_tab(self) -> None:
        icons_dir = Path(__file__).parent / "assets" / "icons"
        layout = QVBoxLayout(self.tab_channels)

        top_h = QHBoxLayout()
        self.input_channel_search = QLineEdit()
        self.input_channel_search.setPlaceholderText("Pesquisar grupo ou canal...")
        self.input_channel_search.textChanged.connect(self._filter_channels)
        top_h.addWidget(self.input_channel_search)

        self.btn_refresh_channels = QPushButton("Recarregar Canais")
        self.btn_refresh_channels.setObjectName("SecondaryButton")
        self.btn_refresh_channels.setIcon(QIcon(str(icons_dir / "arrows-clockwise.svg")))
        self.btn_refresh_channels.clicked.connect(self._load_dialogs)
        top_h.addWidget(self.btn_refresh_channels)
        layout.addLayout(top_h)

        self.table_channels = QTableWidget()
        self.table_channels.setColumnCount(3)
        self.table_channels.setHorizontalHeaderLabels(["ID", "Nome do Chat / Canal", "Tipo"])
        self.table_channels.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_channels.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_channels.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table_channels.doubleClicked.connect(lambda: self._scan_selected_channel())
        layout.addWidget(self.table_channels)

        self.btn_scan = QPushButton("Escanear Mídias do Canal Selecionado")
        self.btn_scan.setObjectName("SuccessButton")
        self.btn_scan.setIcon(QIcon(str(icons_dir / "list-dashes.svg")))
        self.btn_scan.clicked.connect(self._scan_selected_channel)
        layout.addWidget(self.btn_scan)

    def _setup_catalog_tab(self) -> None:
        icons_dir = Path(__file__).parent / "assets" / "icons"
        layout = QVBoxLayout(self.tab_catalog)

        # Banner de Progresso de Escaneamento
        self.scan_progress_card = QFrame()
        self.scan_progress_card.setObjectName("ContentCard")
        sp_layout = QVBoxLayout(self.scan_progress_card)
        sp_layout.setContentsMargins(10, 10, 10, 10)

        self.lbl_scan_status = QLabel("Escaneando mensagens do canal...")
        self.lbl_scan_status.setStyleSheet(f"font-weight: 600; color: {COLOR_ACCENT}; font-size: 13px;")
        sp_layout.addWidget(self.lbl_scan_status)

        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setRange(0, 0)  # Indeterminado inicial
        sp_layout.addWidget(self.scan_progress_bar)

        self.scan_progress_card.hide()
        layout.addWidget(self.scan_progress_card)

        # Barra de filtros
        top_h = QHBoxLayout()
        self.input_filter_keyword = QLineEdit()
        self.input_filter_keyword.setPlaceholderText("Filtrar arquivos na tabela por palavra-chave...")
        self.input_filter_keyword.textChanged.connect(self._apply_table_search)
        top_h.addWidget(self.input_filter_keyword)

        btn_select_all = QPushButton("Selecionar Todos")
        btn_select_all.setObjectName("SecondaryButton")
        btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        top_h.addWidget(btn_select_all)

        btn_deselect_all = QPushButton("Desmarcar Todos")
        btn_deselect_all.setObjectName("SecondaryButton")
        btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        top_h.addWidget(btn_deselect_all)

        btn_export = QPushButton("Exportar Planilha CSV")
        btn_export.setObjectName("SecondaryButton")
        btn_export.setIcon(QIcon(str(icons_dir / "file-csv.svg")))
        btn_export.clicked.connect(self._export_csv)
        top_h.addWidget(btn_export)
        layout.addLayout(top_h)

        self.table_media = QTableWidget()
        self.table_media.setColumnCount(5)
        self.table_media.setHorizontalHeaderLabels(["Baixar", "ID Msg", "Nome do Arquivo", "Tamanho", "Data"])
        self.table_media.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table_media.itemChanged.connect(self._on_table_item_changed)
        layout.addWidget(self.table_media)

        bottom_h = QHBoxLayout()
        self.lbl_selected_summary = QLabel("Total: 0 arquivos (0 B)")
        self.lbl_selected_summary.setStyleSheet(f"font-weight: 600; color: {COLOR_ACCENT};")
        bottom_h.addWidget(self.lbl_selected_summary)

        bottom_h.addStretch()

        self.btn_start_download = QPushButton("Iniciar Download dos Selecionados")
        self.btn_start_download.setObjectName("SuccessButton")
        self.btn_start_download.setIcon(QIcon(str(icons_dir / "download-simple.svg")))
        self.btn_start_download.clicked.connect(self._start_download_selected)
        bottom_h.addWidget(self.btn_start_download)

        layout.addLayout(bottom_h)

    def _setup_downloads_tab(self) -> None:
        icons_dir = Path(__file__).parent / "assets" / "icons"
        layout = QVBoxLayout(self.tab_downloads)

        card = QFrame()
        card.setObjectName("ContentCard")
        c_layout = QVBoxLayout(card)

        self.lbl_download_status = QLabel("Nenhum download em andamento.")
        self.lbl_download_status.setStyleSheet("font-weight: 600; font-size: 14px;")
        c_layout.addWidget(self.lbl_download_status)

        self.global_progress_bar = QProgressBar()
        self.global_progress_bar.setValue(0)
        c_layout.addWidget(self.global_progress_bar)

        h_info = QHBoxLayout()
        self.lbl_speed = QLabel("Velocidade: 0 B/s")
        h_info.addWidget(self.lbl_speed)
        h_info.addStretch()

        self.btn_cancel_download = QPushButton("Cancelar / Parar")
        self.btn_cancel_download.setObjectName("DangerButton")
        self.btn_cancel_download.setIcon(QIcon(str(icons_dir / "stop.svg")))
        self.btn_cancel_download.clicked.connect(self._cancel_download)
        h_info.addWidget(self.btn_cancel_download)
        c_layout.addLayout(h_info)

        layout.addWidget(card)

        layout.addWidget(QLabel("Console de Atividades e Logs em Tempo Real:"))
        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        layout.addWidget(self.txt_logs)

    def _setup_about_tab(self) -> None:
        layout = QVBoxLayout(self.tab_about)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("ElevatedCard")
        c_layout = QVBoxLayout(card)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setContentsMargins(32, 28, 32, 28)
        c_layout.setSpacing(14)

        # Container para a Logo - garante contraste e visibilidade perfeitos
        logo_frame = QFrame()
        logo_frame.setObjectName("LogoBadgeFrame")
        logo_frame.setFixedSize(140, 140)
        lf_layout = QVBoxLayout(logo_frame)
        lf_layout.setContentsMargins(6, 6, 6, 6)
        lf_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        logo_path = Path(__file__).parent / "assets" / "logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            scaled_pix = pix.scaled(
                124, 124,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled_pix)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("LOGO")

        lf_layout.addWidget(logo_label)
        c_layout.addWidget(logo_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Nome e Versão do Software
        title_label = QLabel("Telegram_Downloader_CJrTools")
        title_label.setObjectName("AboutTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(title_label)

        version_label = QLabel("Version 1.0.0")
        version_label.setObjectName("AboutVersion")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(version_label)

        # Linha divisória sutil
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"color: {COLOR_BORDER_SUBTLE}; max-width: 320px;")
        c_layout.addWidget(div, alignment=Qt.AlignmentFlag.AlignCenter)

        # Créditos de Desenvolvimento e Autoria
        credits_label = QLabel(
            "Designed and developed by\n"
            "CJRDOOM\n\n"
            "© 2026 Carlos Junior"
        )
        credits_label.setObjectName("AboutText")
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(credits_label)

        # Badges técnicas
        tech_box = QHBoxLayout()
        tech_box.setSpacing(8)
        tech_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for text in ["Python 3.10+", "PyQt6", "Telethon", "SQLite WAL"]:
            badge = QLabel(text)
            badge.setStyleSheet(
                f"background-color: {COLOR_SURFACE_ACTIVE}; "
                f"border: 1px solid {COLOR_BORDER_SUBTLE}; "
                f"border-radius: 4px; padding: 4px 10px; font-size: 11px; "
                f"color: {COLOR_TEXT_SECONDARY};"
            )
            tech_box.addWidget(badge)

        c_layout.addLayout(tech_box)
        layout.addWidget(card)
        layout.addStretch()

    def _append_log(self, message: str) -> None:
        self.txt_logs.append(message)
        sb = self.txt_logs.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _browse_dest_dir(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Selecione a pasta de download", self.input_dest.text())
        if chosen:
            self.input_dest.setText(chosen)

    def _save_config(self) -> None:
        try:
            if self.input_api_id.text().strip():
                self.config.api_id = int(self.input_api_id.text().strip())
            self.config.api_hash = self.input_api_hash.text().strip()
            self.config.phone = self.input_phone.text().strip()
            self.config.download_path = self.input_dest.text().strip()
            self.config.concurrent_downloads = self.spin_concurrent.value()
            self.config.verify_integrity = self.chk_integrity.isChecked()
            self.config.save_hash = self.chk_hash.isChecked()
            self.config.save()
            QMessageBox.information(self, "Sucesso", "Configurações salvas com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar configurações: {e}")

    def _on_connect_clicked(self) -> None:
        asyncio.create_task(self._connect_telegram())

    async def _connect_telegram(self) -> None:
        self._save_config()
        if not self.config.api_id or not self.config.api_hash or not self.config.phone:
            QMessageBox.warning(self, "Aviso", "Preencha API ID, API Hash e Telefone antes de conectar.")
            return

        self._append_log("Conectando ao Telegram...")
        self.status_badge.setText("Conectando...")
        self.status_badge.setStyleSheet(
            f"background-color: {COLOR_WARNING}; color: #1A1A1A; border-radius: 4px; padding: 4px 10px; font-weight: 600;"
        )

        try:
            self.client = get_telegram_client(self.config)
            await self.client.connect()

            if not await self.client.is_user_authorized():
                self._append_log(f"Enviando código de verificação para {self.config.phone}...")
                await self.client.send_code_request(self.config.phone)

                code, ok = QInputDialog.getText(self, "Código Telegram", f"Digite o código enviado para {self.config.phone}:")
                if not ok or not code.strip():
                    self._append_log("Autenticação cancelada pelo usuário.")
                    return

                try:
                    await self.client.sign_in(phone=self.config.phone, code=code.strip())
                except Exception as e:
                    if "password" in str(e).lower() or "2fa" in str(e).lower():
                        pwd, ok_pwd = QInputDialog.getText(
                            self, "Senha 2FA", "Digite sua senha de autenticação em duas etapas (2FA):",
                            QLineEdit.EchoMode.Password
                        )
                        if ok_pwd and pwd:
                            await self.client.sign_in(password=pwd.strip())
                        else:
                            raise e
                    else:
                        raise e

            self.status_badge.setText("Conectado")
            self.status_badge.setObjectName("StatusBadgeActive")
            self.status_badge.setStyleSheet(
                f"background-color: {COLOR_SUCCESS}; color: #1A1A1A; border-radius: 4px; padding: 4px 10px; font-weight: 600;"
            )
            self._append_log("Autenticado com sucesso no Telegram!")
            self.tabs.setCurrentIndex(1)
            await self._load_dialogs_async()

        except Exception as e:
            self.status_badge.setText("Erro")
            self.status_badge.setStyleSheet(
                f"background-color: {COLOR_ERROR}; color: #FFFFFF; border-radius: 4px; padding: 4px 10px; font-weight: 600;"
            )
            self._append_log(f"Falha na conexão: {e}")
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao Telegram: {e}")

    def _load_dialogs(self) -> None:
        asyncio.create_task(self._load_dialogs_async())

    async def _load_dialogs_async(self) -> None:
        if not self.client or not self.client.is_connected():
            QMessageBox.warning(self, "Aviso", "Conecte-se ao Telegram primeiro.")
            return

        self._append_log("Buscando canais e grupos...")
        self.table_channels.setRowCount(0)
        self._dialog_items = []

        try:
            async for dialog in self.client.iter_dialogs():
                if dialog.is_group or dialog.is_channel:
                    tipo = "Canal" if dialog.is_channel and not dialog.is_group else "Grupo"
                    name = dialog.name or "Sem título"
                    self._dialog_items.append((str(dialog.id), name, tipo, dialog.entity))

            self._filter_channels()
            self._append_log(f"{len(self._dialog_items)} canais/grupos carregados.")
        except Exception as e:
            self._append_log(f"Erro ao carregar canais: {e}")

    def _filter_channels(self) -> None:
        query = self.input_channel_search.text().strip().lower()
        filtered = [d for d in getattr(self, "_dialog_items", []) if query in d[1].lower()]

        self.table_channels.setRowCount(len(filtered))
        for row, (did, name, tipo, entity) in enumerate(filtered):
            self.table_channels.setItem(row, 0, QTableWidgetItem(did))
            self.table_channels.setItem(row, 1, QTableWidgetItem(name))
            self.table_channels.setItem(row, 2, QTableWidgetItem(tipo))
            self.table_channels.item(row, 0).setData(Qt.ItemDataRole.UserRole, entity)

    def _scan_selected_channel(self) -> None:
        if self.is_scanning:
            QMessageBox.warning(self, "Aviso", "Já existe uma varredura em andamento.")
            return

        selected_rows = self.table_channels.selectionModel().selectedRows()
        if not selected_rows:
            # Se não houver linha inteira selecionada, pega a linha do item ativo
            current_row = self.table_channels.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "Aviso", "Selecione um canal ou grupo na tabela.")
                return
            row = current_row
        else:
            row = selected_rows[0].row()

        item = self.table_channels.item(row, 0)
        if not item:
            QMessageBox.warning(self, "Aviso", "Item inválido.")
            return

        entity = item.data(Qt.ItemDataRole.UserRole)
        self.current_entity = entity
        self.scan_task = asyncio.create_task(self._scan_channel_async())

    def _on_scan_progress(self, total_msg: int, total_media: int, total_bytes: int, scan_total: int) -> None:
        title = getattr(self.current_entity, "title", "Canal")
        if scan_total and scan_total > 0:
            self.scan_progress_bar.setRange(0, scan_total)
            self.scan_progress_bar.setValue(total_msg)
            self.lbl_scan_status.setText(
                f"Varrendo '{title}': {total_msg}/{scan_total} mensagens analisadas | "
                f"{total_media} mídias encontradas ({human_readable_size(total_bytes)})"
            )
        else:
            self.scan_progress_bar.setRange(0, 0)
            self.scan_progress_bar.setValue(0)
            self.lbl_scan_status.setText(
                f"Varrendo '{title}': {total_msg} mensagens analisadas | "
                f"{total_media} mídias encontradas ({human_readable_size(total_bytes)})"
            )

    async def _scan_channel_async(self) -> None:
        self.is_scanning = True
        self.btn_scan.setEnabled(False)
        self.scan_progress_card.show()
        self.scan_progress_bar.setRange(0, 0)

        title = getattr(self.current_entity, "title", "Canal")
        self.lbl_scan_status.setText(f"Iniciando varredura para '{title}'...")
        self.tabs.setCurrentIndex(2)  # Muda para aba de catálogo
        self._append_log(f"Iniciando escaneamento de mídias para '{title}'...")

        dest_dir = Path(self.config.download_path).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        def progress_cb(total_msg: int, total_media: int, total_bytes: int, scan_total: int | None):
            self.scan_progress_signal.emit(total_msg, total_media, total_bytes, scan_total or 0)

        try:
            downloader = Downloader(self.client, self.current_entity, dest_dir, self.db, self.config, self.stats)
            result = await downloader.scan_channel(progress_callback=progress_cb)
            self.scanned_files = result.get("files", [])

            self._populate_media_table(self.scanned_files)
            msg = f"Escaneamento concluído: {len(self.scanned_files)} mídias encontradas ({human_readable_size(result['total_bytes'])})."
            self._append_log(msg)
            self.lbl_scan_status.setText(f"✓ {msg}")
        except Exception as e:
            self._append_log(f"Erro no escaneamento: {e}")
            self.lbl_scan_status.setText(f"Erro na varredura: {e}")
            QMessageBox.critical(self, "Erro na Varredura", f"Não foi possível escanear o canal:\n{e}")
        finally:
            self.is_scanning = False
            self.btn_scan.setEnabled(True)
            self.scan_progress_bar.setRange(0, 100)
            self.scan_progress_bar.setValue(100)

    def _populate_media_table(self, files: list[dict[str, Any]]) -> None:
        self.table_media.blockSignals(True)
        self.table_media.setRowCount(len(files))

        for row, f in enumerate(files):
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk_item.setCheckState(Qt.CheckState.Checked)

            self.table_media.setItem(row, 0, chk_item)
            self.table_media.setItem(row, 1, QTableWidgetItem(str(f["message_id"])))
            self.table_media.setItem(row, 2, QTableWidgetItem(f["file_name"]))
            self.table_media.setItem(row, 3, QTableWidgetItem(human_readable_size(f["file_size"])))
            self.table_media.setItem(row, 4, QTableWidgetItem(str(f.get("date", ""))))

            chk_item.setData(Qt.ItemDataRole.UserRole, f)

        self.table_media.blockSignals(False)
        self._update_selected_summary()

    def _on_table_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            self._update_selected_summary()

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.table_media.blockSignals(True)
        for row in range(self.table_media.rowCount()):
            item = self.table_media.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table_media.blockSignals(False)
        self._update_selected_summary()

    def _apply_table_search(self) -> None:
        query = self.input_filter_keyword.text().strip().lower()
        for row in range(self.table_media.rowCount()):
            name_item = self.table_media.item(row, 2)
            if name_item:
                visible = query in name_item.text().lower() if query else True
                self.table_media.setRowHidden(row, not visible)
        self._update_selected_summary()

    def _update_selected_summary(self) -> None:
        count = 0
        total_bytes = 0
        for row in range(self.table_media.rowCount()):
            if self.table_media.isRowHidden(row):
                continue
            item = self.table_media.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                f = item.data(Qt.ItemDataRole.UserRole)
                if f:
                    count += 1
                    total_bytes += f.get("file_size", 0)

        self.lbl_selected_summary.setText(f"Selecionados: {count} arquivo(s) ({human_readable_size(total_bytes)})")

    def _export_csv(self) -> None:
        if not self.scanned_files:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo escaneado para exportar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Catálogo CSV",
            str(get_log_dir() / f"catalogo_{sanitize_filename(getattr(self.current_entity, 'title', 'canal'))}.csv"),
            "Arquivos CSV (*.csv)"
        )
        if file_path:
            exported = export_catalog_csv(self.scanned_files, file_path)
            QMessageBox.information(self, "Sucesso", f"Catálogo exportado com sucesso para:\n{exported}")

    def _start_download_selected(self) -> None:
        selected_files = []
        for row in range(self.table_media.rowCount()):
            item = self.table_media.item(row, 0)
            if item and item.checkState() == Qt.CheckState.Checked:
                f = item.data(Qt.ItemDataRole.UserRole)
                if f:
                    selected_files.append(f)

        if not selected_files:
            QMessageBox.warning(self, "Aviso", "Nenhum arquivo selecionado para download.")
            return

        self.tabs.setCurrentIndex(3)
        self.download_task = asyncio.create_task(self._run_downloads_async(selected_files))

    async def _run_downloads_async(self, files_to_download: list[dict[str, Any]]) -> None:
        self.is_downloading = True
        total_bytes = sum(f["file_size"] for f in files_to_download)
        target_ids = [f["message_id"] for f in files_to_download]

        dest_dir = Path(self.config.download_path).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        self.lbl_download_status.setText(
            f"Baixando {len(files_to_download)} arquivos ({human_readable_size(total_bytes)}) em {dest_dir.name}..."
        )
        self._append_log(f"Iniciando download de {len(files_to_download)} arquivos...")

        downloader = Downloader(self.client, self.current_entity, dest_dir, self.db, self.config, self.stats)

        try:
            await downloader.run(
                initial_total_bytes=total_bytes,
                target_message_ids=target_ids
            )
            self.lbl_download_status.setText("Download concluído com sucesso!")
            self._append_log("Todos os downloads foram concluídos com sucesso!")
            QMessageBox.information(self, "Concluído", "Downloads finalizados com sucesso!")
        except asyncio.CancelledError:
            self.lbl_download_status.setText("Downloads cancelados pelo usuário.")
            self._append_log("Downloads interrompidos.")
        except Exception as e:
            self.lbl_download_status.setText(f"Erro no download: {e}")
            self._append_log(f"Erro durante download: {e}")
            QMessageBox.critical(self, "Erro", f"Ocorreu um erro no download: {e}")
        finally:
            self.is_downloading = False

    def _cancel_download(self) -> None:
        if self.download_task and not self.download_task.done():
            self.download_task.cancel()
            self._append_log("Cancelando downloads...")
