from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import ApplicationDB, ProfileDB
from app.matcher import score_match
from app.job_discovery import discover_and_score
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Job Match Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ApplicationIn(BaseModel):
    company: str
    role: str
    job_description: str
    status: str = "applied"
    notes: str = ""


class ApplicationUpdate(BaseModel):
    company: str | None = None
    role: str | None = None
    job_description: str | None = None
    notes: str | None = None


class ApplicationOut(BaseModel):
    id: int
    company: str
    role: str
    job_description: str
    status: str
    notes: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@app.get("/")
def root():
    return {"message": "Job Match Tracker API"}


@app.post("/applications", response_model=ApplicationOut)
def create_application(app_in: ApplicationIn, db: Session = Depends(get_db)):
    record = ApplicationDB(**app_in.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    return (
        db.query(ApplicationDB)
        .order_by(ApplicationDB.updated_at.desc())
        .all()
    )


@app.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    record = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return record


@app.patch("/applications/{app_id}", response_model=ApplicationOut)
def edit_application(
    app_id: int, updates: ApplicationUpdate, db: Session = Depends(get_db)
):
    record = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
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


@app.delete("/applications/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    record = db.query(ApplicationDB).filter(ApplicationDB.id == app_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(record)
    db.commit()
    return {"deleted": True, "id": app_id}


# ---- Resume Profile: save once, reuse everywhere ----

class ProfileIn(BaseModel):
    resume_text: str


class ProfileOut(BaseModel):
    resume_text: str
    updated_at: datetime

    class Config:
        from_attributes = True


@app.get("/profile", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(ProfileDB).filter(ProfileDB.id == 1).first()
    if not profile:
        raise HTTPException(
            status_code=404, detail="No profile saved yet. POST /profile first."
        )
    return profile

@app.get("/discover-jobs")
def discover_jobs(
    search: str = "",
    category: str = "software-dev",
    limit: int = 20,
    db: Session = Depends(get_db),
):
    profile = db.query(ProfileDB).filter(ProfileDB.id == 1).first()
    if not profile or not profile.resume_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No resume saved. POST /profile with your resume_text first.",
        )

    try:
        results = discover_and_score(
            profile.resume_text, search=search, category=category, limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Couldn't fetch live jobs right now: {e}"
        )

    return results
@app.post("/profile", response_model=ProfileOut)
def save_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    profile = db.query(ProfileDB).filter(ProfileDB.id == 1).first()
    if profile:
        profile.resume_text = payload.resume_text
    else:
        profile = ProfileDB(id=1, resume_text=payload.resume_text)
        db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


# ---- Matching ----

class MatchRequest(BaseModel):
    resume_text: str
    job_description: str


@app.post("/match")
def match_resume_to_job(payload: MatchRequest):
    try:
        return score_match(payload.resume_text, payload.job_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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

    results.sort(key=lambda r: r.match_score, reverse=True)
    return results