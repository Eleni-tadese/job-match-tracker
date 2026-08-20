from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.matcher import score_match
app = FastAPI(title="Job Match Tracker")

# --- In-memory store (swap for a real DB later) ---
applications = {}
next_id = 1


class Application(BaseModel):
    company: str
    role: str
    job_description: str
    status: str = "applied"  # applied, interviewing, rejected, offer


class ApplicationOut(Application):
    id: int


@app.get("/")
def root():
    return {"message": "Job Match Tracker API"}


@app.post("/applications", response_model=ApplicationOut)
def create_application(app_in: Application):
    global next_id
    record = ApplicationOut(id=next_id, **app_in.model_dump())
    applications[next_id] = record
    next_id += 1
    return record


@app.get("/applications", response_model=list[ApplicationOut])
def list_applications():
    return list(applications.values())


@app.get("/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int):
    record = applications.get(app_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    return record


@app.patch("/applications/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, status: str):
    record = applications.get(app_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    record.status = status
    return record

class MatchRequest(BaseModel):
    resume_text: str
    job_description: str


@app.post("/match")
def match_resume_to_job(payload: MatchRequest):
    try:
        result = score_match(payload.resume_text, payload.job_description)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))