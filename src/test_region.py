from pathlib import Path
import pymupdf

PDF_PATH = Path("test-data/catalogs/catalogo-1.pdf")
PAGE_NUMBER = 415   

RECT = pymupdf.Rect(
    0,
    0,
    300,
    200,
)

def main() -> None: 
    document = pymupdf.open(PDF_PATH)
    page = document[PAGE_NUMBER - 1]

    print(f"Página: {PAGE_NUMBER}")
    print(f"Tamanho: {page.rect.width} x {page.rect.height}")

    text = page.get_text(
"text", clip=RECT
    )
