from uuid_extensions import uuid7
from app.utils.database import Base

from sqlalchemy import (
    Column,
    String,
    DateTime,
    func
)

class BaseModel(Base):
    """This model creates helper methods for all models"""

    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid7()))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
