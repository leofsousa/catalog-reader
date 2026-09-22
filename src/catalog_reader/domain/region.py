# src/catalog_reader/domain/region.py

from dataclasses import dataclass


@dataclass
class Region:
    """Uma região retangular em uma página de PDF.

    Coordenadas SEMPRE em pontos PDF (72 DPI), sistema de origem no
    canto superior esquerdo da página. Nunca armazenar em pixels de
    tela: a conversão tela↔PDF depende do zoom e precisa ser feita
    na hora de pintar ou de interpretar eventos de mouse.
    """

    x: float
    y: float
    width: float
    height: float
    name: str = ""

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError(
                f"Region precisa ter width/height positivos, "
                f"recebi width={self.width}, height={self.height}"
            )

    def contains_point(self, px: float, py: float) -> bool:
        """Testa se um ponto (px, py) em espaço PDF está dentro da região."""
        return (
            self.x <= px <= self.x + self.width
            and self.y <= py <= self.y + self.height
        )