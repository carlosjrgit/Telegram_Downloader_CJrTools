"""
Ponto de entrada do loop da aplicação PyQt6 com suporte a qasync.
"""

import asyncio
import sys

import qasync
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import DARK_THEME_QSS


def run_gui() -> None:
    """Inicia a aplicação gráfica PyQt6 integrada com o loop assíncrono do asyncio via qasync."""
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_THEME_QSS)

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    main_win = MainWindow()
    main_win.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    run_gui()
