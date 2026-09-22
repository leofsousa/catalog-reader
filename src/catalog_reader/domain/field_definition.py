# src/catalog_reader/domain/field_definition.py

from dataclasses import dataclass


@dataclass
class FieldDefinition:
    """Modelo visual de um campo, definido pelo usuário.

    NÃO pertence a uma página específica: é um molde que descreve
    'onde ler' em cada página do intervalo. Será aplicado a cada
    página no momento da extração.

    Coordenadas SEMPRE em pontos PDF (72 DPI), sistema de origem
    no canto superior esquerdo da página.

    Atributos:
        name: nome dado pelo usuário (ex.: 'nome-do-animal')
        x, y, width, height: geometria em pontos PDF
        source_page: índice (0-based) da página em que o campo foi
            originalmente desenhado. Usado apenas para exibir o
            retângulo verde na página de referência; a extração
            ignora esse campo.
    """

    name: str
    x: float
    y: float
    width: float
    height: float
    source_page: int = 0

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"FieldDefinition precisa ter width/height positivos, "
                f"recebi width={self.width}, height={self.height}"
            )