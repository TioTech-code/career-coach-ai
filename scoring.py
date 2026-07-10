import re

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

    # Contact
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", cv_text):
        scores["Contact"] += 5

    if re.search(r"\+?\d[\d\s()-]{8,}", cv_text):
        scores["Contact"] += 5

    # Summary
    if any(word in text for word in ["profile", "summary", "objective", "about me"]):
        scores["Summary"] = 10

    # Education
    if "education" in text:
        scores["Education"] = 15

    # Experience
    if any(word in text for word in ["experience", "employment", "work history"]):
        scores["Experience"] = 20

    # Skills
    if "skills" in text:
        scores["Skills"] = 15

    # Projects
    if any(word in text for word in ["projects", "portfolio"]):
        scores["Projects"] = 15

    # ATS headings
    ats_headings = [
        "profile",
        "education",
        "experience",
        "skills",
        "projects"
    ]

    scores["ATS"] = sum(2 for heading in ats_headings if heading in text)

    overall = min(100, int(sum(scores.values())))

    return overall, scores