"""Survey domain objects and the monthly climate-pulse question template."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PreguntaPlantilla:
    """A question included in every automatically generated monthly survey."""

    dimension: str
    texto: str


PLANTILLA_PULSO_MENSUAL = (
    PreguntaPlantilla(
        "bienestar",
        "Me siento bien y con energía durante mi jornada laboral.",
    ),
    PreguntaPlantilla(
        "apoyo",
        "Puedo contar con el apoyo de mi equipo cuando lo necesito.",
    ),
    PreguntaPlantilla(
        "comunicación",
        "La comunicación dentro de mi equipo es clara y respetuosa.",
    ),
    PreguntaPlantilla(
        "reconocimiento",
        "Siento que mi trabajo y esfuerzo son valorados.",
    ),
    PreguntaPlantilla(
        "carga laboral",
        "La carga de trabajo me permite brindar una atención de calidad.",
    ),
)


@dataclass(frozen=True, slots=True)
class PreguntaEncuesta:
    """A persisted question displayed to a survey participant."""

    id: str
    orden: int
    dimension: str
    texto: str


@dataclass(frozen=True, slots=True)
class Encuesta:
    """A monthly survey and its public, non-identifying question data."""

    id: str
    anio: int
    mes: int
    titulo: str
    descripcion: str
    estado: str
    preguntas: tuple[PreguntaEncuesta, ...]
