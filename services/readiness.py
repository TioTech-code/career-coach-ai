import re


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "of", "on", "or", "our", "that",
    "the", "their", "this", "to", "we", "will", "with", "you", "your"
}


def extract_keywords(text):
    """Return useful words from CV or job-description text."""
    words = re.findall(r"[a-zA-Z][a-zA-Z+#.-]{2,}", text.lower())

    return {
        word
        for word in words
        if word not in STOP_WORDS
    }


def calculate_job_match(cv_text, job_description):
    """Calculate a consistent keyword-match score."""
    cv_keywords = extract_keywords(cv_text)
    job_keywords = extract_keywords(job_description)

    if not job_keywords:
        return 0, [], []

    matching_keywords = sorted(cv_keywords & job_keywords)
    missing_keywords = sorted(job_keywords - cv_keywords)

    score = round(
        len(matching_keywords) / len(job_keywords) * 100
    )

    return min(score, 100), matching_keywords, missing_keywords


def calculate_evidence_score(cv_text):
    """Score how strongly the CV supports its claims."""
    text = cv_text.lower()
    score = 0

    action_verbs = [
        "achieved",
        "built",
        "created",
        "delivered",
        "designed",
        "developed",
        "implemented",
        "improved",
        "increased",
        "led",
        "managed",
        "reduced",
        "supported",
    ]

    action_verb_count = sum(
        1 for verb in action_verbs if verb in text
    )

    score += min(action_verb_count * 4, 32)

    measurable_results = re.findall(
        r"\b\d+(?:\.\d+)?%|\b£\d+|\b\d+\s+"
        r"(?:customers?|people|projects?|months?|years?|users?|students?)",
        text,
    )

    score += min(len(measurable_results) * 8, 32)

    if "experience" in text or "employment" in text:
        score += 12

    if "project" in text or "portfolio" in text:
        score += 12

    if "achievement" in text or "award" in text:
        score += 6

    if "github" in text or "linkedin" in text:
        score += 6

    return min(score, 100)


def calculate_readiness_score(
    cv_score,
    job_match_score,
    evidence_score,
):
    """Combine the three scores into one readiness score."""
    readiness_score = round(
        (cv_score * 0.40)
        + (job_match_score * 0.40)
        + (evidence_score * 0.20)
    )

    return min(readiness_score, 100)


def get_readiness_status(score):
    if score >= 85:
        return "Ready to Apply"

    if score >= 70:
        return "Nearly Ready"

    if score >= 55:
        return "Good Foundation"

    return "Needs Improvement"