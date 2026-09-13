"""
Base repository pattern implementation for SQLAlchemy 2.x models.
"""

from typing import Generic, Type, TypeVar, Sequence, Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic CRUD repository wrapping SQLAlchemy sessions."""

    def __init__(self, model: Type[ModelType], db: Session) -> None:
        self.model = model
        self.db = db

    def get_by_id(self, id_val: Any) -> ModelType | None:
        """Fetch a single record by primary key."""
        return self.db.get(self.model, str(id_val))

    def list_all(
        self, limit: int = 100, offset: int = 0, **filters: Any
    ) -> Sequence[ModelType]:
        """Query multiple records with optional simple filters."""
        stmt = select(self.model)
        for key, val in filters.items():
            if hasattr(self.model, key) and val is not None:
                stmt = stmt.filter(getattr(self.model, key) == val)
        stmt = stmt.offset(offset).limit(limit)
        return self.db.scalars(stmt).all()

    def create(self, entity: ModelType) -> ModelType:
        """Persist a new entity into the database."""
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, entity: ModelType, **kwargs: Any) -> ModelType:
        """Update fields on an existing entity."""
        for attr, val in kwargs.items():
            if hasattr(entity, attr) and val is not None:
                setattr(entity, attr, val)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, id_val: Any) -> bool:
        """Delete a record by primary key."""
        obj = self.get_by_id(id_val)
        if not obj:
            return False
        self.db.delete(obj)
        self.db.commit()
        return True
