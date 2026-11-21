"""Declarative base shared by SQLAlchemy persistence adapters."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base metadata for application database models."""
