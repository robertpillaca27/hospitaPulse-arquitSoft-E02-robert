"""PostgreSQL adapter for monthly surveys and anonymous answer persistence."""

from uuid import uuid4

from sqlalchemy import Engine, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.modulos.encuestas.dominio.encuesta import (
    Encuesta,
    PreguntaEncuesta,
    PreguntaPlantilla,
)
from app.modulos.encuestas.dominio.indicadores import (
    IndicadorDimension,
    IndicadoresMensuales,
)
from app.modulos.encuestas.dominio.respuesta_anonima import RespuestaAnonima
from app.modulos.encuestas.infraestructura.models import (
    EncuestaModel,
    PreguntaEncuestaModel,
    RespuestaEncuestaModel,
    RespuestaLikertModel,
)


class PostgresEncuestaRepository:
    """Persist surveys in PostgreSQL with an idempotent monthly uniqueness rule."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener_o_crear_mensual(
        self,
        anio: int,
        mes: int,
        titulo: str,
        descripcion: str,
        preguntas: tuple[PreguntaPlantilla, ...],
    ) -> Encuesta:
        """Return the unique survey for the period or create its default template."""
        survey = self._buscar_periodo(anio, mes)
        if survey is None:
            survey = EncuestaModel(
                id=str(uuid4()),
                anio=anio,
                mes=mes,
                titulo=titulo,
                descripcion=descripcion,
                estado="abierta",
                preguntas=[
                    PreguntaEncuestaModel(
                        id=str(uuid4()),
                        orden=orden,
                        dimension=pregunta.dimension,
                        texto=pregunta.texto,
                    )
                    for orden, pregunta in enumerate(preguntas, start=1)
                ],
            )
            self._session.add(survey)
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                survey = self._buscar_periodo(anio, mes)
                if survey is None:
                    raise

        self._cerrar_periodos_anteriores(anio, mes)
        return self._to_domain(survey)

    def obtener_por_id(self, encuesta_id: str) -> Encuesta | None:
        """Load a survey and its ordered questions by identifier."""
        survey = self._session.scalar(
            select(EncuestaModel)
            .options(joinedload(EncuestaModel.preguntas))
            .where(EncuestaModel.id == encuesta_id)
        )
        return self._to_domain(survey) if survey is not None else None

    def registrar_respuesta(
        self, encuesta_id: str, respuestas: tuple[RespuestaAnonima, ...]
    ) -> None:
        """Persist a response without storing participant identity or service."""
        submission = RespuestaEncuestaModel(id=str(uuid4()), encuesta_id=encuesta_id)
        submission.respuestas = [
            RespuestaLikertModel(
                id=str(uuid4()),
                pregunta_id=respuesta.pregunta_id,
                valor=respuesta.valor,
            )
            for respuesta in respuestas
        ]
        self._session.add(submission)
        self._session.commit()

    def obtener_indicadores_mensuales(
        self, anio: int, mes: int
    ) -> IndicadoresMensuales:
        """Aggregate response counts and Likert averages for a survey period."""
        survey_id = self._session.scalar(
            select(EncuestaModel.id).where(
                EncuestaModel.anio == anio,
                EncuestaModel.mes == mes,
            )
        )
        if survey_id is None:
            return IndicadoresMensuales(
                anio=anio,
                mes=mes,
                enmascarado=True,
                total_respuestas=None,
                promedio_general=None,
                dimensiones=(),
            )

        total_respuestas = self._session.scalar(
            select(func.count(RespuestaEncuestaModel.id)).where(
                RespuestaEncuestaModel.encuesta_id == survey_id
            )
        ) or 0
        if total_respuestas < 5:
            return IndicadoresMensuales(
                anio=anio,
                mes=mes,
                enmascarado=True,
                total_respuestas=total_respuestas,
                promedio_general=None,
                dimensiones=(),
            )

        promedio_general = self._session.scalar(
            select(func.avg(RespuestaLikertModel.valor))
            .join(
                RespuestaEncuestaModel,
                RespuestaEncuestaModel.id == RespuestaLikertModel.respuesta_id,
            )
            .where(RespuestaEncuestaModel.encuesta_id == survey_id)
        )
        promedios_dimension = self._session.execute(
            select(
                PreguntaEncuestaModel.dimension,
                func.avg(RespuestaLikertModel.valor),
            )
            .join(
                RespuestaLikertModel,
                RespuestaLikertModel.pregunta_id == PreguntaEncuestaModel.id,
            )
            .join(
                RespuestaEncuestaModel,
                RespuestaEncuestaModel.id == RespuestaLikertModel.respuesta_id,
            )
            .where(
                PreguntaEncuestaModel.encuesta_id == survey_id,
                RespuestaEncuestaModel.encuesta_id == survey_id,
            )
            .group_by(PreguntaEncuestaModel.dimension)
            .order_by(PreguntaEncuestaModel.dimension)
        ).all()
        return IndicadoresMensuales(
            anio=anio,
            mes=mes,
            enmascarado=False,
            total_respuestas=total_respuestas,
            promedio_general=round(float(promedio_general or 0), 2),
            dimensiones=tuple(
                IndicadorDimension(dimension=dimension, promedio=round(float(promedio), 2))
                for dimension, promedio in promedios_dimension
            ),
        )

    def _buscar_periodo(self, anio: int, mes: int) -> EncuestaModel | None:
        return self._session.scalar(
            select(EncuestaModel)
            .options(joinedload(EncuestaModel.preguntas))
            .where(EncuestaModel.anio == anio, EncuestaModel.mes == mes)
        )

    def _cerrar_periodos_anteriores(self, anio: int, mes: int) -> None:
        self._session.execute(
            update(EncuestaModel)
            .where(
                ((EncuestaModel.anio < anio)
                 | ((EncuestaModel.anio == anio) & (EncuestaModel.mes < mes))),
                EncuestaModel.estado == "abierta",
            )
            .values(estado="cerrada")
        )
        self._session.commit()

    @staticmethod
    def _to_domain(survey: EncuestaModel) -> Encuesta:
        preguntas = tuple(
            PreguntaEncuesta(
                id=pregunta.id,
                orden=pregunta.orden,
                dimension=pregunta.dimension,
                texto=pregunta.texto,
            )
            for pregunta in sorted(survey.preguntas, key=lambda item: item.orden)
        )
        return Encuesta(
            id=survey.id,
            anio=survey.anio,
            mes=survey.mes,
            titulo=survey.titulo,
            descripcion=survey.descripcion,
            estado=survey.estado,
            preguntas=preguntas,
        )


def ensure_current_survey(engine: Engine) -> None:
    """Create the current month's survey when the database has no survey for it."""
    from app.modulos.encuestas.aplicacion.gestionar_encuesta_use_case import (
        GestionarEncuestaUseCase,
    )

    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        GestionarEncuestaUseCase(PostgresEncuestaRepository(session)).obtener_encuesta_actual()
