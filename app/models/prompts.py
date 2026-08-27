from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.models.base_models import BaseModel

class Prompt(BaseModel):
    __tablename__ = "prompts"

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_by_id = Column(String, ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("Admin", backref="created_prompts")

    def __repr__(self):
        return f"Prompt(id={self.id}, name={self.name}, category={self.category}, version={self.version}, is_active={self.is_active})"
