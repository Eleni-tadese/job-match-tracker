from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import ApplicationDB
from app.matcher import score_match

# Creates the applications table in job_tracker.db if it doesn't exist yet.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Match Tracker")


class Application(BaseModel):
    company: str
    role: str
    job_description: str
    status: str = "applied"

    class Config:
        from_attributes = True  # lets us build this from an ORM object


class ApplicationOut(Application):
    id: int


@app.get("/")
def root():
    return {"message": "Job Match Tracker API"}


@app.post("/applications", response_model=ApplicationOut)
def create_application(app_in: Application, db: Session = Depends(get_db)):
    record = ApplicationDB(**app_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return db.query(ApplicationDB).all()


@app.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    record = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return record


@app.patch("/applications/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, status: str, db: Session = Depends(get_db)):
    record = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    record.status = status
    db.commit()
    db.refresh(record)
    return record


class MatchRequest(BaseModel):
    resume_text: str
    job_description: str


@app.post("/match")
def match_resume_to_job(payload: MatchRequest):
    try:
        return score_match(payload.resume_text, payload.job_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
