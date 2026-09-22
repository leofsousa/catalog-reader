# src/catalog_reader/infrastructure/pdf_document.py

from pathlib import Path
import pymupdf


class PdfDocument:
    """Wrapper determinístico sobre um PDF. Não conhece Qt.

    Responsabilidade única: abrir o PDF e entregar dados brutos
    (contagem de páginas, pixmap renderizado, dimensões da página,
    texto de uma região). Toda conversão para tipos do Qt acontece
    na camada de UI.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"PDF não encontrado: {self.path}")
        self._doc = pymupdf.open(str(self.path))
        if self._doc.page_count == 0:
            raise ValueError(f"PDF sem páginas: {self.path}")

    @property
    def page_count(self) -> int:
        return self._doc.page_count

    @property
    def name(self) -> str:
        return self.path.name

    def page_rect(self, page_index: int) -> pymupdf.Rect:
        """Retorna o retângulo da página em pontos PDF (72 DPI).

        É a dimensão "natural" do PDF, independente de zoom. Toda
        coordenada de Region é armazenada neste espaço.
        """
        if not (0 <= page_index < self.page_count):
            raise IndexError(
                f"page_index {page_index} fora do intervalo "
                f"[0, {self.page_count - 1}]"
            )
        page = self._doc.load_page(page_index)
        return page.rect

    def render_page(self, page_index: int, zoom: float = 1.0) -> pymupdf.Pixmap:
        """Renderiza uma página (0-based) e devolve um Pixmap do PyMuPDF.

        zoom=1.0 corresponde a 72 DPI (escala natural do PDF).
        Valores maiores aumentam a resolução de renderização.
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