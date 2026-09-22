# src/catalog_reader/domain/extracted_record.py

from dataclasses import dataclass, field


@dataclass
class ExtractedRecord:
    """Um registro extraído de uma página do PDF.

    Corresponde a um "lote" no vocabulário do catálogo. Nesta etapa
    (escopo "1 lote por página"), cada página gera exatamente um
    ExtractedRecord com lot_index=0. Quando o escopo "personalizado"
    for implementado, uma mesma página poderá gerar vários registros,
    com lot_index=0, 1, 2, ...

    Atributos:
        page: número da página, 1-based (para exibição).
        lot_index: índice do lote dentro da página, 0-based.
        values: mapa nome_do_campo → texto extraído.
    """

    page: int
    lot_index: int
    values: dict[str, str] = field(default_factory=dict)