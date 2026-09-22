# src/catalog_reader/application/extractor.py

import pymupdf

from catalog_reader.infrastructure.pdf_document import PdfDocument
from catalog_reader.domain.field_definition import FieldDefinition
from catalog_reader.domain.extracted_record import ExtractedRecord


def normalize_text(text: str) -> str:
    """Colapsa o texto em uma única linha."""
    return " ".join(text.split())


def extract_field_text(
    page: pymupdf.Page,
    field: FieldDefinition,
) -> str:
    """Extrai o texto de um único campo em uma única página."""
    rect = pymupdf.Rect(
        field.x,
        field.y,
        field.x + field.width,
        field.y + field.height,
    )
    raw = page.get_text("text", clip=rect)
    return normalize_text(raw)


def extract_records(
    document: PdfDocument,
    fields: list[FieldDefinition],
    page_start: int,
    page_end: int,
    progress_callback=None,
) -> list[ExtractedRecord]:
    """Executa a extração sobre o intervalo (escopo 1 lote/página)."""
    if page_start < 1 or page_end < page_start:
        raise ValueError(f"Intervalo inválido: {page_start}..{page_end}")
    if page_end > document.page_count:
        raise ValueError(
            f"Intervalo {page_start}..{page_end} excede o PDF "
            f"({document.page_count} páginas)"
        )

    records: list[ExtractedRecord] = []
    total = page_end - page_start + 1

    for i, page_number in enumerate(range(page_start, page_end + 1)):
        page = document.get_page(page_number - 1)

        values: dict[str, str] = {}
        for field in fields:
            values[field.name] = extract_field_text(page, field)

        records.append(
            ExtractedRecord(
                page=page_number,
                lot_index=0,
                values=values,
            )
        )

        if progress_callback is not None:
            progress_callback(i + 1, total)

    return records
