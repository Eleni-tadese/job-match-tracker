"""
Resume-to-job match scoring.

Uses TF-IDF vectorization + cosine similarity to score how well a resume's
text matches a job description, and surfaces which keywords drove the score.
This is a real (if lightweight) NLP technique, not a hardcoded heuristic —
the same core idea behind tools like Jobscan and resume-matching ATS filters.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re


def _clean(text: str) -> str:
    """Lowercase and strip non-alphanumeric noise so the vectorizer
    focuses on actual words rather than punctuation/formatting artifacts."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_match(resume_text: str, job_description: str, top_n: int = 10) -> dict:
    """
    Returns a match score (0-100) between a resume and a job description,
    plus the top overlapping keywords that contributed to the score.
    """
    resume_clean = _clean(resume_text)
    jd_clean = _clean(job_description)

    if not resume_clean or not jd_clean:
        raise ValueError("Both resume_text and job_description must be non-empty")

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([resume_clean, jd_clean])

    # Cosine similarity between the two TF-IDF vectors → single similarity score
    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    score = round(float(similarity) * 100, 1)

    # Find which terms in the job description carry the most TF-IDF weight
    # AND also appear in the resume — these are the "matched keywords"
    feature_names = vectorizer.get_feature_names_out()
    jd_vector = tfidf_matrix[1].toarray()[0]
    resume_words = set(resume_clean.split())

    scored_terms = [
        (feature_names[i], jd_vector[i])
        for i in jd_vector.argsort()[::-1]
        if jd_vector[i] > 0 and feature_names[i] in resume_words
    ]
    matched_keywords = [term for term, _ in scored_terms[:top_n]]

    # Also surface important JD terms the resume is missing — actionable signal
    missing_terms = [
        feature_names[i]
        for i in jd_vector.argsort()[::-1]
        if jd_vector[i] > 0 and feature_names[i] not in resume_words
    ][:top_n]

    return {
        "match_score": score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_terms,
    }