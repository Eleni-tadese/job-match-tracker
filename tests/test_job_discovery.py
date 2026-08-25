"""
Tests for live job discovery and result scoring formatting (app/job_discovery.py).
"""

from unittest.mock import patch
from app.job_discovery import discover_and_score

MOCK_REMOTIVE_JOBS = [
    {
        "id": 1001,
        "title": "Backend Engineer",
        "company_name": "TechCorp",
        "category": "Software Development",
        "url": "https://remotive.com/job/1001",
        "candidate_required_location": "Worldwide",
        "job_type": "full_time",
        "description": "<p>Looking for a Python and FastAPI developer to build REST APIs.</p>",
    },
    {
        "id": None,
        "title": "Full Stack Developer",
        "company_name": "StartupX",
        "category": "Software Development",
        "url": "https://remotive.com/job/1002",
        "candidate_required_location": "USA",
        "job_type": "full_time",
        "description": "<div>Python, React, PostgreSQL experience required.</div>",
    },
]


@patch("app.job_discovery.fetch_live_jobs")
def test_discover_and_score_returns_serialized_ids_and_categories(mock_fetch):
    mock_fetch.return_value = MOCK_REMOTIVE_JOBS
    resume = "Experienced Python developer with FastAPI and React skills."

    results = discover_and_score(resume_text=resume, limit=10)

    assert len(results) == 2
    assert results[0]["id"] == 1001
    assert isinstance(results[1]["id"], int)  # CRC32 integer fallback
    assert results[0]["category"] == "Software Development"
    assert "match_score" in results[0]
    assert "matched_keywords" in results[0]
