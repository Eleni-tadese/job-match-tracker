"""
Job discovery: pulls real, live remote job listings from Remotive's public
API (https://remotive.com/api/remote-jobs) and scores each one against a
resume using the existing matcher. No scraping — this is Remotive's own
documented API, provided specifically for third-party apps to use.
"""

import re
import zlib
import httpx
from app.matcher import score_match

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"


def _strip_html(text: str) -> str:
    """Remotive job descriptions come as HTML; strip tags for clean text
    before running them through the matcher."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&amp;|&#39;|&quot;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_live_jobs(
    search: str = "", category: str = "software-dev", limit: int = 20
) -> list[dict]:
    """
    Fetches live job listings from Remotive. `search` is a free-text query
    (e.g. "backend"), `category` filters by Remotive's category slugs —
    defaults to "software-dev" so results are actually relevant tech roles.

    Remotive's server-side category filter is unreliable when combined with
    `search`, so we also filter client-side as a safety net. Note: the
    `category` field Remotive actually returns per job is a human-readable
    label like "Software Development", not the URL slug "software-dev" — so
    we match loosely (checking whether the slug's words appear in the label)
    rather than requiring an exact string match.
    """
    params = {"limit": limit}
    if search:
        params["search"] = search
    if category:
        params["category"] = category

    with httpx.Client(timeout=10.0) as client:
        response = client.get(REMOTIVE_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

    jobs = data.get("jobs", [])

    if category:
        # "software-dev" -> ["software", "dev"] -> checked against the
        # human-readable category label Remotive actually returns.
        category_words = category.lower().replace("-", " ").split()
        jobs = [
            j
            for j in jobs
            if any(word in j.get("category", "").lower() for word in category_words)
        ]

    return jobs


def discover_and_score(
    resume_text: str, search: str = "", category: str = "software-dev", limit: int = 20
) -> list[dict]:
    """
    Fetches live jobs and scores each one against the given resume text.
    Returns a list sorted best-match first, skipping any job whose
    description is too short/empty to score meaningfully.
    """
    # Fetch extra since some results get dropped by the client-side category
    # filter in fetch_live_jobs — this keeps the final list close to `limit`.
    jobs = fetch_live_jobs(search=search, category=category, limit=limit * 3)
    results = []

    for job in jobs:
        description = _strip_html(job.get("description", ""))
        if not description:
            continue

        try:
            match = score_match(resume_text, description)
        except ValueError:
            continue

        job_id = job.get("id")
        if job_id is None:
            raw_key = f"{job.get('company_name', '')}-{job.get('title', '')}-{job.get('url', '')}"
            job_id = zlib.crc32(raw_key.encode())
        elif not isinstance(job_id, int):
            try:
                job_id = int(job_id)
            except ValueError:
                job_id = zlib.crc32(str(job_id).encode())

        results.append(
            {
                "id": job_id,
                "title": job.get("title", ""),
                "company_name": job.get("company_name", ""),
                "category": job.get("category", ""),
                "url": job.get("url", ""),
                "candidate_required_location": job.get(
                    "candidate_required_location", ""
                ),
                "job_type": job.get("job_type", ""),
                "description": description,
                "match_score": match["match_score"],
                "matched_keywords": match["matched_keywords"],
                "missing_keywords": match["missing_keywords"],
            }
        )

    results.sort(key=lambda r: r["match_score"], reverse=True)
    return results[:limit]