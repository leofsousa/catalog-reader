# src/catalog_reader/ui/main_window.py

from pathlib import Path

from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QLabel,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QToolBar,
    QStatusBar,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QSpinBox,
    QFormLayout,
)

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.ui.pdf_page_view import PdfPageView
from catalog_reader.domain.field_definition import FieldDefinition


ZOOM_LEVELS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
ZOOM_DEFAULT_INDEX = 2  # 1.0


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Catalog Reader")
        self.resize(1200, 800)

        # --- Estado ------------------------------------------------------
        self._document: PdfDocument | None = None
        self._current_page: int = 0
        self._zoom_index: int = ZOOM_DEFAULT_INDEX
        self._fields: list[FieldDefinition] = []
        # Intervalo de extração (1-based, para o usuário; internamente 0-based)
        self._range_start: int = 1
        self._range_end: int = 1

        # --- UI ----------------------------------------------------------
        self._build_toolbar()
        self._build_central_area()
        self._build_status_bar()
        self._update_ui_state()

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

        toolbar.addSeparator()

        self._action_extract = QAction("Executar extração", self)
        self._action_extract.triggered.connect(self._on_extract)
        toolbar.addAction(self._action_extract)

    def _build_central_area(self) -> None:
        # ------------------------ Sidebar --------------------------------
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(300)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(8)

        title = QLabel("Ferramentas")
        title.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(title)

        self._button_draw = QPushButton("Selecionar região")
        self._button_draw.setCheckable(True)
        self._button_draw.toggled.connect(self._on_toggle_draw_mode)
        sidebar_layout.addWidget(self._button_draw)

        separator_h1 = QFrame()
        separator_h1.setFrameShape(QFrame.HLine)
        separator_h1.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(separator_h1)

        # ------------------------ Intervalo ------------------------------
        interval_title = QLabel("Intervalo de extração")
        interval_title.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(interval_title)

        interval_form = QFormLayout()
        interval_form.setContentsMargins(0, 0, 0, 0)
        interval_form.setSpacing(6)

        self._spin_start = QSpinBox()
        self._spin_start.setMinimum(1)
        self._spin_start.setMaximum(1)
        self._spin_start.valueChanged.connect(self._on_range_changed)
        interval_form.addRow("Página inicial:", self._spin_start)

        self._spin_end = QSpinBox()
        self._spin_end.setMinimum(1)
        self._spin_end.setMaximum(1)
        self._spin_end.valueChanged.connect(self._on_range_changed)
        interval_form.addRow("Página final:", self._spin_end)

        sidebar_layout.addLayout(interval_form)

        self._range_hint = QLabel("")
        self._range_hint.setWordWrap(True)
        sidebar_layout.addWidget(self._range_hint)

        separator_h2 = QFrame()
        separator_h2.setFrameShape(QFrame.HLine)
        separator_h2.setFrameShadow(QFrame.Sunken)
        sidebar_layout.addWidget(separator_h2)

        # ------------------------ Campos --------------------------------
        fields_title = QLabel("Campos definidos")
        fields_title.setStyleSheet("font-weight: bold;")
        sidebar_layout.addWidget(fields_title)

        self._fields_list = QListWidget()
        self._fields_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._fields_list.setFocusPolicy(Qt.NoFocus)
        sidebar_layout.addWidget(self._fields_list, 1)

        # ------------------------ Área do PDF ----------------------------
        self._page_view = PdfPageView()
        self._page_view.setFocusPolicy(Qt.StrongFocus)
        self._page_view.pan_requested.connect(self._on_pan_requested)
        self._page_view.region_drawn.connect(self._on_region_drawn)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(False)
        self._scroll_area.setAlignment(Qt.AlignCenter)
        self._scroll_area.setWidget(self._page_view)
        self._scroll_area.setFrameShape(QFrame.NoFrame)

        self._scroll_area.installEventFilter(self)
        self._page_view.installEventFilter(self)

        # ------------------------ Layout central -------------------------
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        central_layout.addWidget(sidebar)

        divider = QFrame()
        divider.setFrameShape(QFrame.VLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setStyleSheet("background: #8C8C8C;")
        divider.setFixedWidth(1)
        central_layout.addWidget(divider)

        central_layout.addWidget(self._scroll_area, 1)

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
        self._button_draw.setEnabled(has_doc)

        self._spin_start.setEnabled(has_doc)
        self._spin_end.setEnabled(has_doc)

        # Botão "Executar extração": habilitado quando há documento,
        # ao menos um campo, e o intervalo é válido.
        can_extract = (
            has_doc
            and len(self._fields) > 0
            and self._range_start <= self._range_end
        )
        self._action_extract.setEnabled(False)  # extração real na próxima rodada
        # (mantemos desabilitado mesmo com can_extract=True até implementarmos)

        # Atualiza preview dos campos com o novo intervalo
        if has_doc:
            self._page_view.set_extraction_range(
                self._range_start - 1, self._range_end - 1
            )
            self._page_view.set_fields(self._fields)

    def _update_range_hint(self) -> None:
        if self._document is None:
            self._range_hint.setText("")
            return
        if self._range_start > self._range_end:
            self._range_hint.setText(
                "⚠ Página inicial maior que a final."
            )
            self._range_hint.setStyleSheet("color: #E0A030;")
        else:
            total = self._range_end - self._range_start + 1
            self._range_hint.setText(
                f"{total} página(s) serão processadas."
            )
            self._range_hint.setStyleSheet("color: #8C8C8C;")

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

        # Novo documento → reseta tudo
        self._fields.clear()
        self._button_draw.setChecked(False)
        self._page_view.set_draw_mode(False)

        # Reset do intervalo: 1..N
        total = self._document.page_count
        self._spin_start.blockSignals(True)
        self._spin_end.blockSignals(True)
        self._spin_start.setMaximum(total)
        self._spin_end.setMaximum(total)
        self._spin_start.setValue(1)
        self._spin_end.setValue(total)
        self._spin_start.blockSignals(False)
        self._spin_end.blockSignals(False)
        self._range_start = 1
        self._range_end = total

        self._current_page = 0
        self._refresh_fields_list()
        self._update_range_hint()
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
    # Ações — Intervalo
    # ==================================================================

    def _on_range_changed(self) -> None:
        self._range_start = self._spin_start.value()
        self._range_end = self._spin_end.value()
        self._update_range_hint()
        self._update_ui_state()

    # ==================================================================
    # Ações — Pan
    # ==================================================================

    def _on_pan_requested(self, dx: int, dy: int) -> None:
        hbar = self._scroll_area.horizontalScrollBar()
        vbar = self._scroll_area.verticalScrollBar()
        hbar.setValue(hbar.value() - dx)
        vbar.setValue(vbar.value() - dy)

    # ==================================================================
    # Ações — Definir campos
    # ==================================================================

    def _on_toggle_draw_mode(self, checked: bool) -> None:
        if self._document is None:
            self._button_draw.setChecked(False)
            return
        self._page_view.set_draw_mode(checked)
        self._page_view.setFocus()

    def _on_region_drawn(self, x: float, y: float, w: float, h: float) -> None:
        name, ok = QInputDialog.getText(
            self,
            "Nome da informação",
            "Nome da informação:",
        )
        if not ok:
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(
                self,
                "Nome inválido",
                "O nome não pode estar vazio. O campo foi descartado.",
            )
            return

        if any(f.name == name for f in self._fields):
            QMessageBox.warning(
                self,
                "Nome duplicado",
                f"Já existe um campo chamado '{name}'. "
                f"Escolha outro nome. O campo foi descartado.",
            )
            return

        field = FieldDefinition(
            name=name,
            x=x,
            y=y,
            width=w,
            height=h,
            source_page=self._current_page,
        )
        self._fields.append(field)
        self._page_view.set_fields(self._fields)
        self._refresh_fields_list()
        self._update_ui_state()

    def _on_remove_field(self, index: int) -> None:
        """Apaga o campo de índice `index`."""
        if not (0 <= index < len(self._fields)):
            return
        self._fields.pop(index)
        self._page_view.set_fields(self._fields)
        self._refresh_fields_list()
        self._update_ui_state()

    def _refresh_fields_list(self) -> None:
        self._fields_list.clear()
        for i, field in enumerate(self._fields):
            self._fields_list.addItem(self._make_field_item(i, field))

    def _make_field_item(self, index: int, field: FieldDefinition) -> QListWidgetItem:
        item = QListWidgetItem()
        widget = QWidget()
        h = QHBoxLayout(widget)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(6)

        label = QLabel(f"{field.name}  (p.{field.source_page + 1})")
        label.setToolTip(
            f"x={field.x:.0f}  y={field.y:.0f}  "
            f"w={field.width:.0f}  h={field.height:.0f}"
        )
        h.addWidget(label, 1)

        btn_remove = QPushButton("×")
        btn_remove.setFixedWidth(24)
        btn_remove.setToolTip("Apagar este campo")
        btn_remove.clicked.connect(lambda _checked=False, i=index: self._on_remove_field(i))
        h.addWidget(btn_remove, 0)

        item.setSizeHint(widget.sizeHint())
        self._fields_list.addItem(item)
        self._fields_list.setItemWidget(item, widget)
        return item

    # ==================================================================
    # Ações — Extração (placeholder nesta rodada)
    # ==================================================================

    def _on_extract(self) -> None:
        QMessageBox.information(
            self,
            "Em breve",
            "A extração real será implementada na próxima etapa.",
        )

    # ==================================================================
    # Renderização
    # ==================================================================

    def _render_current_page(self) -> None:
        if self._document is None:
            return

        self._page_view.set_zoom(ZOOM_LEVELS[self._zoom_index])
        self._page_view.set_document(self._document)
        self._page_view.set_page(self._current_page)
        self._page_view.set_extraction_range(
            self._range_start - 1, self._range_end - 1
        )
        self._page_view.set_fields(self._fields)

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
        if event.type() == QEvent.KeyPress and watched in (
            self._scroll_area,
            self._page_view,
        ):
            key = event.key()
            mods = event.modifiers()

            if key == Qt.Key_Escape:
                if self._button_draw.isChecked():
                    self._button_draw.setChecked(False)
                    return True

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

        if key == Qt.Key_Escape:
            if self._button_draw.isChecked():
                self._button_draw.setChecked(False)
                event.accept()
                return

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