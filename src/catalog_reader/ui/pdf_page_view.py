# src/catalog_reader/ui/pdf_page_view.py

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.domain.field_definition import FieldDefinition


# Paleta dos overlays
COLOR_DRAWING = QColor(74, 144, 226)         # azul — desenhando agora
COLOR_DRAWING_FILL = QColor(74, 144, 226, 40)
COLOR_SAVED = QColor(80, 200, 120)           # verde — campo salvo
COLOR_SAVED_FILL = QColor(80, 200, 120, 30)
COLOR_PREVIEW_PEN = QColor(80, 200, 120, 180)  # verde tracejado — preview

MIN_DRAW_PIXELS = 5  # abaixo disso, é clique acidental, não desenho


class PdfPageView(QWidget):
    """Widget que renderiza uma página de PDF e overlays de regiões.

    Coordenadas internas:
    - O documento é acessado em pontos PDF.
    - A pintura converte pontos PDF → pixels de widget usando `zoom`.
    - Toda interação de mouse faz a conversão inversa.
    """

    # Sinais
    pan_requested = Signal(int, int)
    region_drawn = Signal(float, float, float, float)  # x, y, w, h em PDF

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: PdfDocument | None = None
        self._page_index: int = 0
        self._zoom: float = 1.0

        # Campos definidos pelo usuário (compartilhados entre páginas)
        self._fields: list[FieldDefinition] = []

        # Intervalo de extração (0-based, inclusivo)
        self._range_start: int = 0
        self._range_end: int = 0

        # Estado do pan
        self._pan_active = False
        self._pan_start_pos: QPointF | None = None

        # Estado do desenho
        self._draw_mode: bool = False
        self._draw_start_pdf: QPointF | None = None
        self._draw_current_pdf: QPointF | None = None

        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_document(self, document: PdfDocument | None) -> None:
        self._document = document
        self._page_index = 0
        self._refresh_size()

    def set_page(self, page_index: int) -> None:
        if self._document is None:
            return
        if not (0 <= page_index < self._document.page_count):
            return
        self._page_index = page_index
        self._refresh_size()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._refresh_size()

    def set_fields(self, fields: list[FieldDefinition]) -> None:
        """Substitui a lista de campos a exibir."""
        self._fields = list(fields)
        self.update()

    def set_extraction_range(self, start: int, end: int) -> None:
        """Define o intervalo (0-based, inclusivo) de preview válido."""
        self._range_start = start
        self._range_end = end
        self.update()

    def set_draw_mode(self, enabled: bool) -> None:
        self._draw_mode = enabled
        if enabled:
            self.setCursor(Qt.CrossCursor)
        else:
            self.unsetCursor()
            self._draw_start_pdf = None
            self._draw_current_pdf = None
            self.update()

    @property
    def page_index(self) -> int:
        return self._page_index

    @property
    def zoom(self) -> float:
        return self._zoom

    @property
    def draw_mode(self) -> bool:
        return self._draw_mode

    # ------------------------------------------------------------------
    # Conversão de coordenadas
    # ------------------------------------------------------------------

    def pdf_to_widget(self, x: float, y: float) -> tuple[float, float]:
        return x * self._zoom, y * self._zoom

    def widget_to_pdf(self, x: float, y: float) -> tuple[float, float]:
        return x / self._zoom, y / self._zoom

    def _widget_pos_to_pdf(self, pos: QPointF) -> QPointF:
        px, py = self.widget_to_pdf(pos.x(), pos.y())
        return QPointF(px, py)

    # ------------------------------------------------------------------
    # Dimensionamento
    # ------------------------------------------------------------------

    def _refresh_size(self) -> None:
        if self._document is None:
            self.setMinimumSize(1, 1)
            self.resize(1, 1)
            self.update()
            return

        rect = self._document.page_rect(self._page_index)
        w = int(round(rect.width * self._zoom))
        h = int(round(rect.height * self._zoom))
        self.setMinimumSize(w, h)
        self.resize(w, h)
        self.update()

    # ------------------------------------------------------------------
    # Pintura
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.fillRect(self.rect(), self.palette().window().color())

        if self._document is None:
            painter.end()
            return

        # 1) Página renderizada
        pdf_pixmap = self._document.render_page(
            self._page_index, zoom=self._zoom
        )
        image = QImage(
            pdf_pixmap.samples,
            pdf_pixmap.width,
            pdf_pixmap.height,
            pdf_pixmap.stride,
            QImage.Format_RGB888,
        ).copy()
        page_pixmap = QPixmap.fromImage(image)
        painter.drawPixmap(0, 0, page_pixmap)

        # 2) Overlays
        self._paint_fields(painter)
        self._paint_drawing(painter)

        painter.end()

    def _paint_fields(self, painter: QPainter) -> None:
        """Desenha cada campo definido.

        Regras:
        - Na página em que foi desenhado (source_page): verde sólido.
          (Sempre mostrado — o usuário está editando.)
        - Em outras páginas, SE a página estiver dentro do intervalo
          de extração: verde tracejado translúcido (preview).
        - Fora do intervalo: não desenha.
        """
        if not self._fields:
            return

        for field in self._fields:
            is_source = field.source_page == self._page_index
            in_range = self._range_start <= self._page_index <= self._range_end

            if not is_source and not in_range:
                continue

            x1, y1 = self.pdf_to_widget(field.x, field.y)
            x2, y2 = self.pdf_to_widget(
                field.x + field.width, field.y + field.height
            )
            rect = QRectF(x1, y1, x2 - x1, y2 - y1)

            if is_source:
                painter.setPen(QPen(COLOR_SAVED, 2))
                painter.setBrush(COLOR_SAVED_FILL)
            else:
                painter.setPen(QPen(COLOR_PREVIEW_PEN, 2, Qt.DashLine))
                painter.setBrush(Qt.NoBrush)

            painter.drawRect(rect)

    def _paint_drawing(self, painter: QPainter) -> None:
        if self._draw_start_pdf is None or self._draw_current_pdf is None:
            return

        x1_pdf = min(self._draw_start_pdf.x(), self._draw_current_pdf.x())
        y1_pdf = min(self._draw_start_pdf.y(), self._draw_current_pdf.y())
        x2_pdf = max(self._draw_start_pdf.x(), self._draw_current_pdf.x())
        y2_pdf = max(self._draw_start_pdf.y(), self._draw_current_pdf.y())

        x1, y1 = self.pdf_to_widget(x1_pdf, y1_pdf)
        x2, y2 = self.pdf_to_widget(x2_pdf, y2_pdf)

        painter.setPen(QPen(COLOR_DRAWING, 2, Qt.DashLine))
        painter.setBrush(COLOR_DRAWING_FILL)
        painter.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))

    # ------------------------------------------------------------------
    # Mouse — pan e desenho
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        # Pan: botão do meio, ou Ctrl + esquerdo
        is_middle = event.button() == Qt.MiddleButton
        is_ctrl_left = (
            event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        )
        if is_middle or is_ctrl_left:
            self._pan_active = True
            self._pan_start_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        # Desenho: botão esquerdo em modo de desenho
        if self._draw_mode and event.button() == Qt.LeftButton:
            self._draw_start_pdf = self._widget_pos_to_pdf(event.position())
            self._draw_current_pdf = self._draw_start_pdf
            self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._pan_active:
            current = event.position()
            delta = current - self._pan_start_pos
            self._pan_start_pos = current
            self.pan_requested.emit(int(delta.x()), int(delta.y()))
            event.accept()
            return

        if self._draw_mode and self._draw_start_pdf is not None:
            self._draw_current_pdf = self._widget_pos_to_pdf(event.position())
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._pan_active:
            self._pan_active = False
            self._pan_start_pos = None
            if self._draw_mode:
                self.setCursor(Qt.CrossCursor)
            else:
                self.unsetCursor()
            event.accept()
            return

        if (
            self._draw_mode
            and event.button() == Qt.LeftButton
            and self._draw_start_pdf is not None
        ):
            end_pdf = self._widget_pos_to_pdf(event.position())
            start_pdf = self._draw_start_pdf

            x_pdf = min(start_pdf.x(), end_pdf.x())
            y_pdf = min(start_pdf.y(), end_pdf.y())
            w_pdf = abs(end_pdf.x() - start_pdf.x())
            h_pdf = abs(end_pdf.y() - start_pdf.y())

            w_px = w_pdf * self._zoom
            h_px = h_pdf * self._zoom

            self._draw_start_pdf = None
            self._draw_current_pdf = None
            self.update()

            if w_px >= MIN_DRAW_PIXELS and h_px >= MIN_DRAW_PIXELS:
                self.region_drawn.emit(x_pdf, y_pdf, w_pdf, h_pdf)

            event.accept()
            return

        super().mouseReleaseEvent(event)