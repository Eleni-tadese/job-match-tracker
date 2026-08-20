from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class ApplicationDB(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String, default="applied")
