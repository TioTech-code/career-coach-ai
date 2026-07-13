import re

TECHNICAL_SKILLS = [
    "python", "java", "javascript", "html", "css",
    "react", "flask", "django", "sql", "git",
    "docker", "aws", "azure", "c++", "c#"
]

SOFT_SKILLS = [
    "communication", "teamwork", "leadership",
    "problem solving", "organisation",
    "time management", "critical thinking"
]

ACTION_VERBS = [
    "developed", "created", "designed", "built",
    "implemented", "managed", "improved",
    "led", "delivered", "achieved"
]


def score_cv(cv_text):

    text = cv_text.lower()

    scores = {
        "Contact": 0,
        "Summary": 0,
        "Education": 0,
        "Experience": 0,
        "Skills": 0,
        "Projects": 0,
        "ATS": 0,
        "Grammar": 5
    }

    # ------------------
    # Contact (10)
    # ------------------

    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cv_text):
        scores["Contact"] += 4

    if re.search(r"\+?\d[\d\s()-]{8,}", cv_text):
        scores["Contact"] += 4

    if "linkedin" in text or "github" in text:
        scores["Contact"] += 2

    # ------------------
    # Summary (10)
    # ------------------

    if "summary" in text or "profile" in text:
        scores["Summary"] += 4

    if len(text.split()) > 80:
        scores["Summary"] += 3

    if any(skill in text for skill in TECHNICAL_SKILLS):
        scores["Summary"] += 3

    # ------------------
    # Education (15)
    # ------------------

    if "education" in text:
        scores["Education"] += 10

    if "university" in text or "college" in text or "gcse" in text:
        scores["Education"] += 5

    # ------------------
    # Experience (20)
    # ------------------

    if "experience" in text:
        scores["Experience"] += 5

    verbs = sum(1 for verb in ACTION_VERBS if verb in text)

    scores["Experience"] += min(verbs, 5)

    if re.search(r"\d+%|\d+\s*(years?|months?|people|projects?)", text):
        scores["Experience"] += 5

    if "managed" in text or "led" in text:
        scores["Experience"] += 5

    # ------------------
    # Skills (15)
    # ------------------

    skills_found = 0

    for skill in TECHNICAL_SKILLS + SOFT_SKILLS:
        if skill in text:
            skills_found += 1

    scores["Skills"] = min(15, skills_found)

    # ------------------
    # Projects (15)
    # ------------------

    if "project" in text:
        scores["Projects"] += 8

    if "github" in text:
        scores["Projects"] += 4

    if "portfolio" in text:
        scores["Projects"] += 3

    # ------------------
    # ATS (10)
    # ------------------

    headings = [
        "summary",
        "education",
        "experience",
        "skills",
        "projects"
    ]

    scores["ATS"] = min(
        10,
        sum(2 for heading in headings if heading in text)
    )

    overall = min(100, sum(scores.values()))

    return overall, scores