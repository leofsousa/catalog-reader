# src/catalog_reader/ui/main_window.py

from pathlib import Path

from PySide6.QtCore import Qt, QEvent
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
    QSplitter,
    QVBoxLayout,
    QFrame,
)

from catalog_reader.infrastructure.pdf_document import PdfDocument


# Zoom: passos fixos para manter comportamento previsível
ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
ZOOM_DEFAULT_INDEX = 2  # 1.0


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Catalog Reader")
        self.resize(1200, 800)

        # --- Estado da aplicação -----------------------------------------
        self._document: PdfDocument | None = None
        self._current_page: int = 0            # 0-based
        self._zoom_index: int = ZOOM_DEFAULT_INDEX

        # --- Construção da UI --------------------------------------------
        self._build_toolbar()
        self._build_central_area()
        self._build_status_bar()
        self._update_ui_state()

    # ==================================================================
    # Construção da UI
    # ==================================================================

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

        toolbar.addSeparator()

        self._action_zoom_out = QAction("− Zoom", self)
        self._action_zoom_out.triggered.connect(self._on_zoom_out)
        toolbar.addAction(self._action_zoom_out)

        self._action_zoom_in = QAction("+ Zoom", self)
        self._action_zoom_in.triggered.connect(self._on_zoom_in)
        toolbar.addAction(self._action_zoom_in)

        self._action_zoom_reset = QAction("100%", self)
        self._action_zoom_reset.triggered.connect(self._on_zoom_reset)
        toolbar.addAction(self._action_zoom_reset)

    def _build_central_area(self) -> None:
        # ------------------------ Sidebar --------------------------------
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setMinimumWidth(200)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        title = QLabel("Ferramentas")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        sidebar_layout.addWidget(title)

        # Área reservada para as ferramentas (preenchida em etapa futura)
        tools_placeholder = QLabel("(em breve: seleção de regiões)")
        tools_placeholder.setStyleSheet("color: #888; font-size: 12px;")
        tools_placeholder.setWordWrap(True)
        sidebar_layout.addWidget(tools_placeholder)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(separator)

        fields_title = QLabel("Campos definidos")
        fields_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        sidebar_layout.addWidget(fields_title)

        fields_placeholder = QLabel("Nenhum campo definido.")
        fields_placeholder.setStyleSheet("color: #888; font-size: 12px;")
        fields_placeholder.setWordWrap(True)
        sidebar_layout.addWidget(fields_placeholder)

        sidebar_layout.addStretch(1)

        # ------------------------ Área do PDF ----------------------------
        self._page_label = QLabel(
            "Nenhum PDF carregado.\nUse “+ Add PDF” para começar."
        )
        self._page_label.setAlignment(Qt.AlignCenter)
        self._page_label.setStyleSheet("color: #666; font-size: 14px;")

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setAlignment(Qt.AlignCenter)
        self._scroll_area.setWidget(self._page_label)

        # ------------------------ Splitter -------------------------------
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(sidebar)
        splitter.addWidget(self._scroll_area)
        splitter.setStretchFactor(0, 0)   # sidebar: tamanho preferencial
        splitter.setStretchFactor(1, 1)   # viewer: absorve o redimensionamento
        splitter.setSizes([260, 940])     # largura inicial

        self._scroll_area.installEventFilter(self)
        self._page_label.installEventFilter(self)
        self.setCentralWidget(splitter)

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Pronto")

    # ==================================================================
    # Estado da UI
    # ==================================================================

    def _update_ui_state(self) -> None:
        has_doc = self._document is not None
        self._action_prev.setEnabled(has_doc and self._current_page > 0)
        self._action_next.setEnabled(
            has_doc and self._current_page < self._document.page_count - 1
        )
        self._action_zoom_in.setEnabled(
            has_doc and self._zoom_index < len(ZOOM_LEVELS) - 1
        )
        self._action_zoom_out.setEnabled(has_doc and self._zoom_index > 0)
        self._action_zoom_reset.setEnabled(has_doc)

    # ==================================================================
    # Ações — PDF e navegação
    # ==================================================================

    def _on_add_pdf(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione um catálogo PDF",
            str(Path.home()),
            "PDF (*.pdf)",
        )
        if not file_path:
            return

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

    def _on_goto_first_page(self) -> None:
        if self._document is None or self._current_page == 0:
            return
        self._current_page = 0
        self._render_current_page()
        self._update_ui_state()

    def _on_goto_last_page(self) -> None:
        if self._document is None:
            return
        last = self._document.page_count - 1
        if self._current_page == last:
            return
        self._current_page = last
        self._render_current_page()
        self._update_ui_state()

    # ==================================================================
    # Ações — Zoom
    # ==================================================================

    def _on_zoom_in(self) -> None:
        if self._document is None:
            return
        if self._zoom_index >= len(ZOOM_LEVELS) - 1:
            return
        self._zoom_index += 1
        self._render_current_page()
        self._update_ui_state()

    def _on_zoom_out(self) -> None:
        if self._document is None:
            return
        if self._zoom_index <= 0:
            return
        self._zoom_index -= 1
        self._render_current_page()
        self._update_ui_state()

    def _on_zoom_reset(self) -> None:
        if self._document is None:
            return
        self._zoom_index = ZOOM_DEFAULT_INDEX
        self._render_current_page()
        self._update_ui_state()

    # ==================================================================
    # Renderização
    # ==================================================================

    def _render_current_page(self) -> None:
        if self._document is None:
            return

        zoom = ZOOM_LEVELS[self._zoom_index]
        pixmap = self._document.render_page(self._current_page, zoom=zoom)

        image = QImage(
            pixmap.samples,
            pixmap.width,
            pixmap.height,
            pixmap.stride,
            QImage.Format_RGB888,
        ).copy()

        self._page_label.setPixmap(QPixmap.fromImage(image))
        self._page_label.setText("")
        self._page_label.adjustSize()

        zoom_pct = int(round(zoom * 100))
        self._status.showMessage(
            f"{self._document.name} — página "
            f"{self._current_page + 1} de {self._document.page_count} "
            f"— zoom {zoom_pct}%"
        )

    # ==================================================================
    # Teclado
    # ==================================================================
    def eventFilter(self, watched, event) -> bool:
        
        if event.type() == QEvent.KeyPress and watched in (
            self._scroll_area,
            self._page_label,
        ):
            key = event.key()
            mods = event.modifiers()

            if key == Qt.Key_Right:
                self._on_next_page()
                return True
            if key == Qt.Key_Left:
                self._on_prev_page()
                return True
            if key == Qt.Key_Home:
                self._on_goto_first_page()
                return True
            if key == Qt.Key_End:
                self._on_goto_last_page()
                return True

            if mods & Qt.ControlModifier:
                if key in (Qt.Key_Plus, Qt.Key_Equal):
                    self._on_zoom_in()
                    return True
                if key == Qt.Key_Minus:
                    self._on_zoom_out()
                    return True
                if key == Qt.Key_0:
                    self._on_zoom_reset()
                    return True

        return super().eventFilter(watched, event)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mods = event.modifiers()

        if key == Qt.Key_Right:
            self._on_next_page()
            event.accept()
            return
        if key == Qt.Key_Left:
            self._on_prev_page()
            event.accept()
            return
        if key == Qt.Key_Home:
            self._on_goto_first_page()
            event.accept()
            return
        if key == Qt.Key_End:
            self._on_goto_last_page()
            event.accept()
            return

        # Ctrl + '+' / Ctrl + '-' / Ctrl + '0'
        if mods & Qt.ControlModifier:
            if key in (Qt.Key_Plus, Qt.Key_Equal):
                self._on_zoom_in()
                event.accept()
                return
            if key == Qt.Key_Minus:
                self._on_zoom_out()
                event.accept()
                return
            if key == Qt.Key_0:
                self._on_zoom_reset()
                event.accept()
                return

        super().keyPressEvent(event)

    # ==================================================================
    # Ciclo de vida
    # ==================================================================

    def closeEvent(self, event) -> None:
        if self._document is not None:
            self._document.close()
            self._document = None
        super().closeEvent(event)