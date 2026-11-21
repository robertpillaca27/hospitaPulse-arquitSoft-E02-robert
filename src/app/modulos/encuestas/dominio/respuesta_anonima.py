"""Anonymous survey answer value object."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RespuestaAnonima:
    """A Likert answer that contains no respondent identity."""

    pregunta_id: str
    valor: int

    def __post_init__(self) -> None:
        if not self.pregunta_id:
            raise ValueError("Cada respuesta debe indicar una pregunta.")
        if isinstance(self.valor, bool) or not 1 <= self.valor <= 5:
            raise ValueError("El valor de cada respuesta debe estar entre 1 y 5.")
