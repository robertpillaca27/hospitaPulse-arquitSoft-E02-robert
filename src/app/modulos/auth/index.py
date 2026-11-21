"""API pública del módulo de autenticación.

Añade aquí re-exportaciones de casos de uso y contratos disponibles para otros
módulos. Este archivo no debe exponer adaptadores de infraestructura.
"""

"""Public authentication module contracts."""

from app.modulos.auth.infraestructura.credentials import PasswordHasher

__all__ = ["PasswordHasher"]
