"""
Tests for the resume-job matching engine (app/matcher.py).

Run with: pytest
"""

import pytest
from app.matcher import score_match


def test_strong_match_returns_high_score():
    resume = "Experienced Python developer with FastAPI, PostgreSQL, and React skills. Built REST APIs and worked with Docker."
    job_description = "Looking for a backend developer with Python, FastAPI, PostgreSQL experience. Docker and CI/CD a plus."

    result = score_match(resume, job_description)

    assert result["match_score"] > 20  # meaningfully above zero
    assert "python" in result["matched_keywords"]
    assert "fastapi" in result["matched_keywords"]


def test_total_mismatch_returns_near_zero_score():
    resume = "Experienced graphic designer skilled in Photoshop, Illustrator, and brand identity design."
    job_description = "Looking for a backend developer with Python, FastAPI, PostgreSQL experience. Docker and CI/CD a plus."

    result = score_match(resume, job_description)

    assert result["match_score"] == 0
    assert result["matched_keywords"] == []


def test_matched_keywords_only_include_words_in_both_texts():
    resume = "Python developer with Docker experience."
    job_description = "Looking for a Python developer. React experience is a plus."

    result = score_match(resume, job_description)

    assert "python" in result["matched_keywords"]
    # "react" appears only in the job description, not the resume
    assert "react" not in result["matched_keywords"]
    assert "react" in result["missing_keywords"]


def test_empty_resume_raises_value_error():
    with pytest.raises(ValueError):
        score_match("", "Looking for a Python developer.")


def test_empty_job_description_raises_value_error():
    with pytest.raises(ValueError):
        score_match("Python developer with FastAPI experience.", "")


def test_scoring_is_case_insensitive():
    resume = "PYTHON DEVELOPER"
    job_description = "python developer"

    result = score_match(resume, job_description)

    assert result["match_score"] > 0
    assert "python" in result["matched_keywords"]