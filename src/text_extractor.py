# src/test_extractor.py
#
# Teste isolado do motor de extração. Não depende de UI.
# Uso:
#   python src/test_extractor.py

from pathlib import Path
import sys

# Adiciona src/ ao sys.path para permitir import de catalog_reader.*
# (necessário porque este script fica fora do pacote)
sys.path.insert(0, str(Path(__file__).resolve().parent))

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.domain.field_definition import FieldDefinition
from catalog_reader.application.extractor import extract_records


def main() -> None:
    pdf_path = Path("test-data/catalogs/catalogo-1.pdf")
    if not pdf_path.exists():
        print(f"PDF não encontrado: {pdf_path}")
        return

    document = PdfDocument(pdf_path)
    print(f"PDF: {document.name} — {document.page_count} páginas")

    # Vamos extrair uma área qualquer da primeira página só para
    # validar o mecanismo. Coordenadas em pontos PDF.
    # Ajuste esses valores conforme o layout do seu PDF.
    page_rect = document.page_rect(0)
    print(f"Dimensões da página 1: {page_rect.width} x {page_rect.height} pontos")

    # Campos de teste: pegamos 3 faixas horizontais da página
    fields = [
        FieldDefinition(name="faixa_topo",    x=0, y=0,
                        width=page_rect.width, height=100),
        FieldDefinition(name="faixa_meio",    x=0, y=page_rect.height/2 - 50,
                        width=page_rect.width, height=100),
        FieldDefinition(name="faixa_baixo",   x=0, y=page_rect.height - 100,
                        width=page_rect.width, height=100),
    ]

    # Extrai da página 1 à página 1 (só a primeira)
    records = extract_records(
        document=document,
        fields=fields,
        page_start=1,
        page_end=1,
    )

    for r in records:
        print(f"\n=== Página {r.page} / lote {r.lot_index} ===")
        for name, value in r.values.items():
            preview = value[:120] + ("..." if len(value) > 120 else "")
            print(f"  {name}: {preview!r}")

    document.close()


if __name__ == "__main__":
    main()