"""Roles recognized by the HospitaPulse personnel access model."""

from enum import StrEnum


class RolPersonal(StrEnum):
    """Least-privilege application roles."""

    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    STAFF = "staff"
