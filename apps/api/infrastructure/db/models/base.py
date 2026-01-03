"""
SQLAlchemy Declarative Base.

Minimal base class - no mixins to avoid injecting columns
into tables that don't have them (e.g., checkpoint_writes has no id/created_at).
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
