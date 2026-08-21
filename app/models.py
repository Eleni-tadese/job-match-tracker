from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class ApplicationDB(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    job_description = Column(Text, nullable=False)
    status = Column(String, default="applied")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class ProfileDB(Base):
    """
    Single-user profile: stores the resume text once so it doesn't need to
    be re-pasted on every match request. Always uses id=1 (upsert pattern) —
    this app has no auth/multi-user support, so one profile row is enough.
    """
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, default=1)
    resume_text = Column(Text, default="")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)