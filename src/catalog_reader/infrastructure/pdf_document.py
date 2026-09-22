# src/catalog_reader/infrastructure/pdf_document.py

from pathlib import Path
import pymupdf


class PdfDocument:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {self.path}")
        # pymupdf.open aceita str ou Path; convertemos para str por segurança
        self._doc = pymupdf.open(str(self.path))
        if self._doc.page_count == 0:
            raise ValueError(f"PDF sem páginas: {self.path}")

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def name(self) -> str:
        return self.path.name

    def render_page(self, page_index: int, zoom: float = 1.5) -> pymupdf.Pixmap:
        """Renderiza uma página (0-based) e devolve um Pixmap do PyMuPDF.

        zoom=1.5 é um valor de conforto visual (108 DPI).
        Zoom ajustável virá em etapa futura.
        """
        if not (0 <= page_index < self.page_count):
            raise IndexError(
                f"page_index {page_index} fora do intervalo "
                f"[0, {self.page_count - 1}]"
            )
        page = self._doc.load_page(page_index)
        matrix = pymupdf.Matrix(zoom, zoom)
        return page.get_pixmap(matrix=matrix, alpha=False)

    def close(self) -> None:
        self._doc.close()