from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import ApplicationDB
from app.matcher import score_match

from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Match Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Application(BaseModel):
    company: str
    role: str
    job_description: str
    status: str = "applied"

    class Config:
        from_attributes = True


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


# ---- New: batch scoring across all saved applications ----

class BatchMatchRequest(BaseModel):
    resume_text: str


class BatchMatchResult(BaseModel):
    id: int
    company: str
    role: str
    match_score: float
    matched_keywords: list[str]
    missing_keywords: list[str]


@app.post("/applications/match-resume", response_model=list[BatchMatchResult])
def match_resume_against_all(payload: BatchMatchRequest, db: Session = Depends(get_db)):
    """
    Scores one resume against every saved application's job description,
    and returns the results ranked best-match first. This turns the
    single-pair matcher into a real "which of my saved jobs am I the
    strongest fit for" tool.
    """
    applications = db.query(ApplicationDB).all()

    if not applications:
        raise HTTPException(
            status_code=404,
            detail="No saved applications to match against. Add some via POST /applications first.",
        )

    results = []
    for application in applications:
        try:
            match = score_match(payload.resume_text, application.job_description)
        except ValueError:
            # Skip any application with an empty/unusable job description
            # rather than failing the whole batch for one bad record.
            continue

        results.append(
            BatchMatchResult(
                id=application.id,
                company=application.company,
                role=application.role,
                match_score=match["match_score"],
                matched_keywords=match["matched_keywords"],
                missing_keywords=match["missing_keywords"],
            )
        )

    # Best match first
    results.sort(key=lambda r: r.match_score, reverse=True)
    return results