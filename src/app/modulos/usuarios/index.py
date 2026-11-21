"""API pública del módulo de usuarios.

Añade aquí re-exportaciones de casos de uso y contratos disponibles para otros
módulos. Este archivo no debe exponer adaptadores de infraestructura.
"""

"""Public personnel module contracts and use cases."""

from app.modulos.usuarios.aplicacion.gestionar_personal_use_case import (
    GestionarPersonalUseCase,
    NuevoUsuarioPersonal,
    UsuarioPersonal,
)
from app.modulos.usuarios.dominio.rol_personal import RolPersonal

__all__ = [
    "GestionarPersonalUseCase",
    "NuevoUsuarioPersonal",
    "RolPersonal",
    "UsuarioPersonal",
]
