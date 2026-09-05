"""
Design System Oficial - Telegram_Downloader_CJrTools
Estética: Dark, Minimal, Flat, Geometric e Technical.
Diretriz: 'Flat, not plain'. Sem gradientes, glassmorphism, 3D ou bordas excessivamente arredondadas.
"""

from __future__ import annotations

# Design Tokens Oficiais
COLOR_BACKGROUND = "#2E2D2D"
COLOR_SURFACE = "#363535"
COLOR_SURFACE_ELEVATED = "#3D3C3C"
COLOR_SURFACE_ACTIVE = "#454444"
COLOR_SURFACE_DISABLED = "#303030"

COLOR_ACCENT = "#FFAC2B"
COLOR_BORDER_STRONG = "#9E9E9E"
COLOR_BORDER_SUBTLE = "#4A4949"

COLOR_TEXT_PRIMARY = "#F0F0F0"
COLOR_TEXT_SECONDARY = "#BDBDBD"
COLOR_TEXT_DISABLED = "#666666"

COLOR_SUCCESS = "#22C55E"
COLOR_WARNING = "#EAB308"
COLOR_ERROR = "#EF4444"
COLOR_INFO = "#3B82F6"

FONT_PRIMARY = "Inter, 'Segoe UI', -apple-system, sans-serif"
FONT_MONOSPACE = "'JetBrains Mono', 'Consolas', 'Cascadia Code', monospace"

RADIUS_DEFAULT = 4
RADIUS_SUBTLE = 2
BORDER_WIDTH_DEFAULT = 1

DARK_THEME_QSS = f"""
/* =========================================================================
   CONFIGURAÇÃO GLOBAL DA APLICAÇÃO (DARK, MINIMAL, FLAT, GEOMETRIC)
   ========================================================================= */
QWidget {{
    background-color: {COLOR_BACKGROUND};
    color: {COLOR_TEXT_PRIMARY};
    font-family: {FONT_PRIMARY};
    font-size: 14px;
    selection-background-color: {COLOR_ACCENT};
    selection-color: #1A1A1A;
}}

/* =========================================================================
   SUPERFÍCIES E CARDS
   ========================================================================= */
QFrame#HeaderCard {{
    background-color: {COLOR_SURFACE};
    border-radius: {RADIUS_DEFAULT}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    padding: 12px 16px;
}}

QFrame#ContentCard {{
    background-color: {COLOR_SURFACE};
    border-radius: {RADIUS_DEFAULT}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    padding: 16px;
}}

QFrame#ElevatedCard {{
    background-color: {COLOR_SURFACE_ELEVATED};
    border-radius: {RADIUS_DEFAULT}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    padding: 16px;
}}

/* Container dedicado para exibição da Logo garantindo contraste perfeito */
QFrame#LogoBadgeFrame {{
    background-color: #FFFFFF;
    border-radius: {RADIUS_DEFAULT}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_STRONG};
    padding: 8px;
}}

/* =========================================================================
   SISTEMA DE ABAS (QTabWidget / QTabBar)
   ========================================================================= */
QTabWidget::pane {{
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    background-color: {COLOR_SURFACE};
    border-radius: {RADIUS_DEFAULT}px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLOR_SURFACE};
    color: {COLOR_TEXT_SECONDARY};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-bottom: none;
    border-top-left-radius: {RADIUS_DEFAULT}px;
    border-top-right-radius: {RADIUS_DEFAULT}px;
    padding: 10px 20px;
    margin-right: 4px;
    font-weight: 500;
    font-size: 13px;
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLOR_SURFACE_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
}}

QTabBar::tab:selected {{
    background-color: {COLOR_SURFACE_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border-color: {COLOR_BORDER_STRONG};
    border-top: 2px solid {COLOR_ACCENT};
    font-weight: 600;
}}

/* =========================================================================
   BOTÕES (Primary, Secondary, Danger, Success, Ghost, Icon)
   ========================================================================= */
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: #1A1A1A;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_ACCENT};
    border-radius: {RADIUS_DEFAULT}px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 14px;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: #E59A26;
    border-color: #E59A26;
}}

QPushButton:pressed {{
    background-color: #CC8820;
    border-color: #CC8820;
}}

QPushButton:disabled {{
    background-color: {COLOR_SURFACE_DISABLED};
    color: {COLOR_TEXT_DISABLED};
    border-color: {COLOR_BORDER_SUBTLE};
}}

QPushButton#SecondaryButton {{
    background-color: {COLOR_SURFACE_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    font-weight: 500;
}}

QPushButton#SecondaryButton:hover {{
    background-color: {COLOR_SURFACE_ACTIVE};
    border-color: {COLOR_BORDER_STRONG};
}}

QPushButton#SecondaryButton:pressed {{
    background-color: #303030;
}}

QPushButton#DangerButton {{
    background-color: {COLOR_ERROR};
    color: #FFFFFF;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_ERROR};
}}

QPushButton#DangerButton:hover {{
    background-color: #DC2626;
    border-color: #DC2626;
}}

QPushButton#DangerButton:pressed {{
    background-color: #B91C1C;
    border-color: #B91C1C;
}}

QPushButton#SuccessButton {{
    background-color: {COLOR_SUCCESS};
    color: #FFFFFF;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_SUCCESS};
}}

QPushButton#SuccessButton:hover {{
    background-color: #16A34A;
    border-color: #16A34A;
}}

QPushButton#SuccessButton:pressed {{
    background-color: #15803D;
    border-color: #15803D;
}}

QPushButton#GhostButton {{
    background-color: transparent;
    color: {COLOR_TEXT_PRIMARY};
    border: {BORDER_WIDTH_DEFAULT}px solid transparent;
}}

QPushButton#GhostButton:hover {{
    background-color: {COLOR_SURFACE_ELEVATED};
    border-color: {COLOR_BORDER_SUBTLE};
}}

/* =========================================================================
   INPUTS, SPINBOX, COMBOBOX
   ========================================================================= */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {COLOR_BACKGROUND};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-radius: {RADIUS_DEFAULT}px;
    padding: 7px 12px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 14px;
}}

QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {COLOR_BORDER_STRONG};
}}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_ACCENT};
    background-color: {COLOR_SURFACE};
}}

QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{
    background-color: {COLOR_SURFACE_DISABLED};
    color: {COLOR_TEXT_DISABLED};
    border-color: {COLOR_BORDER_SUBTLE};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_SURFACE_ELEVATED};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_SURFACE_ACTIVE};
    selection-color: {COLOR_TEXT_PRIMARY};
}}

/* =========================================================================
   TABELAS E CABEÇALHOS (QTableWidget)
   ========================================================================= */
QTableWidget {{
    background-color: {COLOR_BACKGROUND};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-radius: {RADIUS_DEFAULT}px;
    gridline-color: {COLOR_BORDER_SUBTLE};
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
}}

QTableWidget::item {{
    padding: 6px 8px;
    border-bottom: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
}}

QTableWidget::item:selected {{
    background-color: {COLOR_SURFACE_ACTIVE};
    color: {COLOR_TEXT_PRIMARY};
    border-left: 2px solid {COLOR_ACCENT};
}}

QHeaderView::section {{
    background-color: {COLOR_SURFACE_ELEVATED};
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 600;
    font-size: 13px;
    border: none;
    border-right: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-bottom: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    padding: 8px 6px;
}}

/* =========================================================================
   BARRAS DE PROGRESSO (QProgressBar - FLAT, 2px radius, chunk ACCENT)
   ========================================================================= */
QProgressBar {{
    background-color: {COLOR_BACKGROUND};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-radius: {RADIUS_SUBTLE}px;
    text-align: center;
    color: {COLOR_TEXT_PRIMARY};
    font-weight: 600;
    font-size: 12px;
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: {RADIUS_SUBTLE}px;
}}

/* =========================================================================
   CHECKBOXES
   ========================================================================= */
QCheckBox {{
    spacing: 8px;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: {RADIUS_DEFAULT}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_STRONG};
    background-color: {COLOR_BACKGROUND};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_ACCENT};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_ACCENT};
    border-color: {COLOR_ACCENT};
    image: none;
}}

/* =========================================================================
   SCROLLBARS (MINIMALISTAS E RETAS)
   ========================================================================= */
QScrollBar:vertical {{
    background-color: {COLOR_BACKGROUND};
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLOR_SURFACE_ELEVATED};
    min-height: 24px;
    border-radius: {RADIUS_SUBTLE}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLOR_BORDER_STRONG};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BACKGROUND};
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLOR_SURFACE_ELEVATED};
    min-width: 24px;
    border-radius: {RADIUS_SUBTLE}px;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
}}

/* =========================================================================
   DISPLAYS DE TEXTO TÉCNICO E LOGS (JETBRAINS MONO)
   ========================================================================= */
QTextEdit, QPlainTextEdit {{
    background-color: #242323;
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-radius: {RADIUS_DEFAULT}px;
    color: {COLOR_TEXT_PRIMARY};
    font-family: {FONT_MONOSPACE};
    font-size: 13px;
    padding: 10px;
}}

/* =========================================================================
   TIPOGRAFIA E LABELS
   ========================================================================= */
QLabel#TitleLabel {{
    font-size: 22px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel#SubtitleLabel {{
    font-size: 13px;
    color: {COLOR_TEXT_SECONDARY};
}}

QLabel#SectionTitle {{
    font-size: 16px;
    font-weight: 600;
    color: {COLOR_TEXT_PRIMARY};
}}

QLabel#AboutTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {COLOR_ACCENT};
}}

QLabel#AboutVersion {{
    font-size: 14px;
    font-weight: 500;
    color: {COLOR_TEXT_SECONDARY};
}}

QLabel#AboutText {{
    font-size: 13px;
    color: {COLOR_TEXT_PRIMARY};
    line-height: 1.5;
}}

/* Badges de Status */
QLabel#StatusBadgeActive {{
    background-color: {COLOR_SUCCESS};
    color: #1A1A1A;
    border-radius: {RADIUS_DEFAULT}px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 12px;
}}

QLabel#StatusBadgeInactive {{
    background-color: {COLOR_SURFACE_DISABLED};
    color: {COLOR_TEXT_DISABLED};
    border: {BORDER_WIDTH_DEFAULT}px solid {COLOR_BORDER_SUBTLE};
    border-radius: {RADIUS_DEFAULT}px;
    padding: 4px 10px;
    font-weight: 600;
    font-size: 12px;
}}
"""
