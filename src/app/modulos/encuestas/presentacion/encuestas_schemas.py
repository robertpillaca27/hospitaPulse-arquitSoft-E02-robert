"""Public request and response schemas for the survey API."""

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class PreguntaResponse(BaseModel):
    """Question fields required by the anonymous survey form."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    orden: int
    dimension: str
    texto: str


class EncuestaResponse(BaseModel):
    """Public survey metadata and Likert questions."""

    id: str
    anio: int
    mes: int
    titulo: str
    descripcion: str
    estado: str
    preguntas: list[PreguntaResponse]


class RespuestaItemRequest(BaseModel):
    """A single strict 1-5 Likert answer."""

    model_config = ConfigDict(extra="forbid")

    pregunta_id: StrictStr = Field(min_length=1)
    valor: StrictInt = Field(ge=1, le=5)


class RegistrarRespuestasRequest(BaseModel):
    """Complete anonymous answer submission."""

    model_config = ConfigDict(extra="forbid")

    respuestas: list[RespuestaItemRequest] = Field(min_length=1)


class RegistrarRespuestasResponse(BaseModel):
    """Identity-free acknowledgment returned after submission."""

    status: str
    mensaje: str
    anonima: bool


class IndicadorDimensionResponse(BaseModel):
    """Average for one dimension after the privacy threshold is met."""

    dimension: str
    promedio: float


class IndicadoresResponse(BaseModel):
    """Privacy-safe aggregate results for a requested survey month."""

    anio: int
    mes: int
    enmascarado: bool
    total_respuestas: int | None
    promedio_general: float | None
    dimensiones: list[IndicadorDimensionResponse]
