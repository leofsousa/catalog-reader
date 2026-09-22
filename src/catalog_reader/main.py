# src/catalog_reader/main.py

import sys

from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication

from catalog_reader.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # --- Paleta global escura ---
    palette = QPalette()

    # Fundo geral das janelas (o cinza/preto "de fundo")
    palette.setColor(QPalette.ColorRole.Window, QColor("#000000"))

    # Fundo de botões, toolbar, sidebar
    palette.setColor(QPalette.ColorRole.Button, QColor("#595859"))

    # Fundo de áreas "dentro" (listas, campos de texto)
    palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))

    # Texto principal
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#E0E0E0"))

    # Texto secundário / desabilitado
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor("#8C8C8C"),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor("#8C8C8C"),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor("#8C8C8C"),
    )

    # Seleção (mantém azul padrão, funciona bem em fundo escuro)
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4A90E2"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

    # Tooltip (fundo escuro, texto claro)
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#595859"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#E0E0E0"))

    app.setPalette(palette)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())