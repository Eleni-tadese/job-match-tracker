from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite file lives in the project root as job_tracker.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./job_tracker.db"

# check_same_thread=False is needed only for SQLite when used with FastAPI's
# threaded request handling — each request gets its own session anyway.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it after
    the request, even if an error occurs."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
