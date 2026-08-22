from sqlalchemy import Column, String, DateTime, Boolean
from app.models.base_models import BaseModel
from app.models.enums import AdminRole
from datetime import datetime

class Admin(BaseModel):
    __tablename__ = "admins"

    first_name: str = Column(String, nullable=False)
    last_name: str = Column(String, nullable=False)
    email: str = Column(String, unique=True, index=True, nullable=False)
    password: str = Column(String, nullable=False)
    phone: str = Column(String, nullable=True)
    gender: str = Column(String, nullable=True)
    role: str = Column(String, default=AdminRole.SUB_ADMIN.value, nullable=False)
    is_active: bool = Column(Boolean, default=True)
    last_login: datetime = Column(DateTime, nullable=True)
    created_by: str = Column(String, nullable=True)
    updated_by: str = Column(String, nullable=True)
    
    def __repr__(self):
        return f"Admin(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, email={self.email}, role={self.role})"

