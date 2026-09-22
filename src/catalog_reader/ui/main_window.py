# src/catalog_reader/ui/main_window.py

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QStatusBar,
)

from catalog_reader.infrastructure.pdf_document import PdfDocument


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Catalog Reader")
        self.resize(1200, 800)

        # Estado da aplicação (por enquanto, só o documento e a página atual)
        self._document: PdfDocument | None = None
        self._current_page: int = 0  # 0-based

        self._build_toolbar()
        self._build_central_area()
        self._build_status_bar()
        self._update_ui_state()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Principal")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._action_add_pdf = QAction("+ Add PDF", self)
        self._action_add_pdf.triggered.connect(self._on_add_pdf)
        toolbar.addAction(self._action_add_pdf)

        toolbar.addSeparator()

        self._action_prev = QAction("◀ Anterior", self)
        self._action_prev.triggered.connect(self._on_prev_page)
        toolbar.addAction(self._action_prev)

        self._action_next = QAction("Próxima ▶", self)
        self._action_next.triggered.connect(self._on_next_page)
        toolbar.addAction(self._action_next)

    def _build_central_area(self) -> None:
        # Um QLabel dentro de um QScrollArea para caber páginas grandes
        self._page_label = QLabel("Nenhum PDF carregado.\nUse “+ Add PDF” para começar.")
        self._page_label.setAlignment(Qt.AlignCenter)
        self._page_label.setStyleSheet("color: #666; font-size: 14px;")

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignCenter)
        self._scroll_area.setWidget(self._page_label)

        self.setCentralWidget(self._scroll_area)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Pronto")

    def _update_ui_state(self) -> None:
        """Habilita/desabilita ações conforme o estado atual."""
        has_doc = self._document is not None
        self._action_prev.setEnabled(has_doc and self._current_page > 0)
        self._action_next.setEnabled(
            has_doc and self._current_page < self._document.page_count - 1
        )

    def _on_add_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione um catálogo PDF",
            str(Path.home()),
            "PDF (*.pdf)",
        )
        if not file_path:
            return  # usuário cancelou

        # Fecha documento anterior, se houver
        if self._document is not None:
            self._document.close()
            self._document = None

        try:
            self._document = PdfDocument(file_path)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao abrir PDF",
                f"Não foi possível abrir o arquivo:\n\n{exc}",
            )
            self._page_label.setText("Nenhum PDF carregado.")
            self._update_ui_state()
            return

        self._current_page = 0
        self._render_current_page()
        self._update_ui_state()

    def _on_prev_page(self) -> None:
        if self._document is None or self._current_page == 0:
            return
        self._current_page -= 1
        self._render_current_page()
        self._update_ui_state()

    def _on_next_page(self) -> None:
        if self._document is None:
            return
        if self._current_page >= self._document.page_count - 1:
            return
        self._current_page += 1
        self._render_current_page()
        self._update_ui_state()

    # ------------------------------------------------------------------
    # Renderização
    # ------------------------------------------------------------------

    def _render_current_page(self) -> None:
        if self._document is None:
            return

        pixmap = self._document.render_page(self._current_page)

        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888,
        ).copy()  # .copy() desacopla do buffer do pixmap, que será descartado

        self._page_label.setPixmap(QPixmap.fromImage(image))
        self._page_label.setText("")  # limpa mensagem de placeholder
        self._page_label.adjustSize()

        self._status.showMessage(
            f"{self._document.name} — página "
            f"{self._current_page + 1} de {self._document.page_count}"
        )

    def closeEvent(self, event) -> None:
        if self._document is not None:
            self._document.close()
            self._document = None
        super().closeEvent(event)