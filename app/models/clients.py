from sqlalchemy import Column, String
from app.models.base_models import BaseModel

class Client(BaseModel):
    __tablename__ = "clients"

    first_name: str = Column(String, nullable=False)
    last_name: str = Column(String, nullable=False)
    email: str = Column(String, unique=True, index=True, nullable=False)
    phone: str = Column(String, nullable=True)

    def __repr__(self):
        return f"Client(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, email={self.email})"
