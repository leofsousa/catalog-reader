# src/catalog_reader/ui/main_window.py

from pathlib import Path

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QWidget,
    QLabel,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QToolBar,
    QStatusBar,
    QVBoxLayout,
    QFrame,
)

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.ui.pdf_page_view import PdfPageView


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

        # Foco inicial na área do PDF para que as setas funcionem de imediato
        self._page_view.setFocus()

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
        sidebar.setFixedWidth(260)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(10)

        title = QLabel("Ferramentas")
        title.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(title)

        tools_placeholder = QLabel("(em breve: seleção de regiões)")
        tools_placeholder.setWordWrap(True)
        sidebar_layout.addWidget(tools_placeholder)

        separator_h = QFrame()
        separator_h.setFrameShape(QFrame.HLine)
        separator_h.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(separator_h)

        fields_title = QLabel("Campos definidos")
        fields_title.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(fields_title)

        fields_placeholder = QLabel("Nenhum campo definido.")
        fields_placeholder.setWordWrap(True)
        sidebar_layout.addWidget(fields_placeholder)

        sidebar_layout.addStretch(1)

        # ------------------------ Área do PDF ----------------------------
        self._page_view = PdfPageView()
        self._page_view.setFocusPolicy(Qt.StrongFocus)
        self._page_view.pan_requested.connect(self._on_pan_requested)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setAlignment(Qt.AlignCenter)
        self._scroll_area.setWidget(self._page_view)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        self._scroll_area.installEventFilter(self)
        self._page_view.installEventFilter(self)

        # ------------------------ Layout central -------------------------
        # Ordem importa: criar o QWidget e o layout ANTES de adicionar
        # qualquer widget nele.
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        central_layout.addWidget(sidebar)

        # Linha divisória fina (visual, não arrastável)
        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setStyleSheet("background: #8C8C8C;")
        divider.setFixedWidth(1)
        central_layout.addWidget(divider)

        central_layout.addWidget(self._scroll_area, 1)  # 1 = absorve o crescimento

        self.setCentralWidget(central)

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
            self._update_ui_state()
            return

        self._current_page = 0
        self._render_current_page()
        self._update_ui_state()
        self._page_view.setFocus()

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
    # Ações — Pan (arrastar para navegar)
    # ==================================================================

    def _on_pan_requested(self, dx: int, dy: int) -> None:
        """Move as barras de rolagem do QScrollArea conforme o arrasto.

        O scroll é invertido em relação ao delta do mouse: arrastar para
        a direita move o conteúdo para a direita, ou seja, o scroll vai
        para a esquerda.
        """
        hbar = self._scroll_area.horizontalScrollBar()
        vbar = self._scroll_area.verticalScrollBar()
        hbar.setValue(hbar.value() - dx)
        vbar.setValue(vbar.value() - dy)

    # ==================================================================
    # Renderização
    # ==================================================================

    def _render_current_page(self) -> None:
        if self._document is None:
            return

        self._page_view.set_zoom(ZOOM_LEVELS[self._zoom_index])
        self._page_view.set_document(self._document)
        self._page_view.set_page(self._current_page)

        zoom_pct = int(round(ZOOM_LEVELS[self._zoom_index] * 100))
        self._status.showMessage(
            f"{self._document.name} — página "
            f"{self._current_page + 1} de {self._document.page_count} "
            f"— zoom {zoom_pct}%"
        )

    # ==================================================================
    # Teclado
    # ==================================================================

    def eventFilter(self, watched, event) -> bool:
        """Intercepta teclas do scroll area e do page view antes que virem
        rolagem. Sem isso, QScrollArea trata ← / → / Home / End como
        comandos de rolagem e o evento nunca chega em keyPressEvent.
        """
        if event.type() == QEvent.KeyPress and watched in (
            self._scroll_area,
            self._page_view,
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