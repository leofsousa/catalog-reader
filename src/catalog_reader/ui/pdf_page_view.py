# src/catalog_reader/ui/pdf_page_view.py

from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF, Signal

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.domain.region import Region


class PdfPageView(QWidget):
    """..."""
    pan_requested = Signal(int, int)   # (dx, dy) em pixels de scroll
    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: PdfDocument | None = None
        self._page_index: int = 0
        self._zoom: float = 1.0
        self._regions: list[Region] = []
        self._pan_active = False
        self._pan_start_pos = None
        self._pan_start_scroll = None

        # Um widget que se pinta inteiramente não deve ter fundo automático
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def set_document(self, document: PdfDocument | None) -> None:
        self._document = document
        self._page_index = 0
        self._regions = []
        self._refresh_size()

    def set_page(self, page_index: int) -> None:
        if self._document is None:
            return
        if not (0 <= page_index < self._document.page_count):
            return
        self._page_index = page_index
        self._regions = []   # placeholder: futuramente buscará regiões da página
        self._refresh_size()

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._refresh_size()

    def set_regions(self, regions: list[Region]) -> None:
        """Substitui a lista de regiões a exibir. Por enquanto, ninguém chama."""
        self._regions = list(regions)
        self.update()

    @property
    def page_index(self) -> int:
        return self._page_index

    @property
    def zoom(self) -> float:
        return self._zoom

    # ------------------------------------------------------------------
    # Conversão de coordenadas
    # ------------------------------------------------------------------

    def pdf_to_widget(self, x: float, y: float) -> tuple[float, float]:
        """Converte um ponto em espaço PDF para pixels deste widget."""
        return x * self._zoom, y * self._zoom

    def widget_to_pdf(self, x: float, y: float) -> tuple[float, float]:
        """Converte um ponto em pixels deste widget para espaço PDF."""
        return x / self._zoom, y / self._zoom

    # ------------------------------------------------------------------
    # Dimensionamento
    # ------------------------------------------------------------------

    def _refresh_size(self) -> None:
        """Ajusta o sizeHint do widget ao tamanho da página em zoom atual.

        Sem isso, o QScrollArea não sabe o quão grande o conteúdo é e
        não exibe barras de rolagem corretas.
        """
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

        # Fundo neutro (cinza claro) — o branco da página destaca
        painter.fillRect(self.rect(), QColor("#e0e0e0"))

        if self._document is None:
            painter.end()
            return

        # 1) Renderiza a página como pixmap
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

        # 2) Desenha as regiões por cima (vazio nesta etapa)
        self._paint_regions(painter)

        painter.end()

    def _paint_regions(self, painter: QPainter) -> None:
        if not self._regions:
            return
        # Reservado para a Sub-etapa 2B
        for region in self._regions:
            x1, y1 = self.pdf_to_widget(region.x, region.y)
            x2, y2 = self.pdf_to_widget(
                region.x + region.width, region.y + region.height
            )
            painter.drawRect(QRectF(x1, y1, x2 - x1, y2 - y1))
            
    # ------------------------------------------------------------------
    # Pan (arrastar para navegar)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        is_middle = event.button() == Qt.MiddleButton
        is_ctrl_left = (
            event.button() == Qt.LeftButton
            and event.modifiers() & Qt.ControlModifier
        )
        if is_middle or is_ctrl_left:
            self._pan_active = True
            self._pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self._pan_active:
            super().mouseMoveEvent(event)
            return

        current = event.position().toPoint()
        delta = current - self._pan_start_pos
        # Emitimos o delta acumulado desde o início do pan;
        # o MainWindow traduz em deslocamento das barras de rolagem.
        self.pan_requested.emit(delta.x(), delta.y())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._pan_active:
            self._pan_active = False
            self._pan_start_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)