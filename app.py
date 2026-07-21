from decorators import pro_required
import stripe
import json
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import inspect, text
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)

from groq import Groq
from dotenv import load_dotenv
from pypdf import PdfReader
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from extensions import db, login_manager
from models import User, Review, JobApplication

from services.scoring import score_cv
from services.rewriter import improve_cv
from services.readiness import (
    calculate_job_match,
    calculate_evidence_score,
    calculate_readiness_score,
    get_readiness_status,
)

import markdown
import os

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
def rate_limit_key():
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return get_remote_address()


limiter = Limiter(
    key_func=rate_limit_key,
    app=app,
    default_limits=["200 per day", "50 per hour"],
)

app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

with app.app_context():
    db.create_all()

    inspector = inspect(db.engine)

    user_columns = {
        column["name"]
        for column in inspector.get_columns("user")
    }

    if "subscription" not in user_columns:
        db.session.execute(
            text(
                """
                ALTER TABLE "user"
                ADD COLUMN subscription VARCHAR(20)
                NOT NULL DEFAULT 'Free'
                """
            )
        )

    if "stripe_customer_id" not in user_columns:
        db.session.execute(
            text(
                """
                ALTER TABLE "user"
                ADD COLUMN stripe_customer_id VARCHAR(255)
                """
            )
        )

    if "stripe_subscription_id" not in user_columns:
        db.session.execute(
            text(
                """
                ALTER TABLE "user"
                ADD COLUMN stripe_subscription_id VARCHAR(255)
                """
            )
        )

    db.session.commit()
os.makedirs(
    app.config["UPLOAD_FOLDER"],
    exist_ok=True,
)

cclient = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
@login_required
def dashboard():

    print("Subscription:", current_user.subscription)
    print("User ID:", current_user.id)
    reviews = (
        Review.query
        .filter_by(user_id=current_user.id)
        .order_by(Review.created_at.asc())
        .all()
    )

    applications = JobApplication.query.filter_by(
        user_id=current_user.id
    ).all()

    total_reviews = len(reviews)
    total_applications = len(applications)

    status_counts = {
        "Saved": 0,
        "Applied": 0,
        "Interview": 0,
        "Offer": 0,
        "Rejected": 0,
    }

    for application in applications:
        if application.status in status_counts:
            status_counts[application.status] += 1

    applied_count = status_counts["Applied"]
    interview_count = status_counts["Interview"]
    offer_count = status_counts["Offer"]

    if reviews:
        scores = [review.score for review in reviews]

        score_labels = [
            review.created_at.strftime("%d %b")
            for review in reviews
        ]

        latest_score = scores[-1]
        previous_score = scores[-2] if len(scores) > 1 else None
        best_score = max(scores)
        average_score = round(sum(scores) / len(scores))

        improvement = (
            latest_score - previous_score
            if previous_score is not None
            else None
        )

    else:
        scores = []
        score_labels = []
        latest_score = None
        previous_score = None
        best_score = None
        average_score = None
        improvement = None

    return render_template(
        "dashboard.html",
        user=current_user,
        total_reviews=total_reviews,
        latest_score=latest_score,
        previous_score=previous_score,
        best_score=best_score,
        average_score=average_score,
        improvement=improvement,
        total_applications=total_applications,
        applied_count=applied_count,
        interview_count=interview_count,
        offer_count=offer_count,
        score_labels=score_labels,
        score_values=scores,
        job_status_labels=list(status_counts.keys()),
        job_status_values=list(status_counts.values()),
    )

@app.route("/cv-review")
@login_required
def cv_review():
    return render_template("cv_review.html")


@app.route("/review", methods=["POST"])
@login_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def review():
    cv_text = ""

    uploaded_file = request.files.get("cv_file")

    if uploaded_file and uploaded_file.filename:
        filename = secure_filename(uploaded_file.filename)

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename,
        )

        uploaded_file.save(filepath)

        try:
            reader = PdfReader(filepath)

            for page in reader.pages:
                text = page.extract_text()

                if text:
                    cv_text += text + "\n"

        except Exception:
            return render_template(
                "cv_review.html",
                error="We could not read that PDF. Please try another file or paste your CV.",
            )

    else:
        cv_text = request.form.get("cv", "").strip()

    if not cv_text:
        return render_template(
            "cv_review.html",
            error="Please upload a PDF or paste your CV.",
        )

    overall_score, score_breakdown = score_cv(cv_text)

    review_prompt = f"""
You are an experienced professional CV reviewer.

IMPORTANT:
Do not give an overall score because the application already calculates one.

Review this CV for any profession.

Use these headings only:

# 💪 Strengths
Give three bullet points.

# ⚠️ Improvements
Give three bullet points.

# 🛠 Recommended Skills
Suggest three useful skills.

# 🎤 Interview Questions
Generate three interview questions.

# 🚀 Final Advice
Write one short paragraph.

Do not invent qualifications, experience, skills or achievements.

CV:

{cv_text}
"""

    recruiter_prompt = f"""
You are a professional recruiter assessing a CV before deciding whether
the candidate should progress.

Assess only the evidence contained in the CV.
Do not invent qualifications, experience, skills or achievements.

Return valid JSON only, using exactly this structure:

{{
    "verdict": "Shortlist" or "Possible Shortlist" or "Do Not Shortlist",
    "confidence": 0,
    "strengths": [
        "First strength",
        "Second strength",
        "Third strength"
    ],
    "concerns": [
        "First concern",
        "Second concern",
        "Third concern"
    ],
    "advice": "One short paragraph of final recruiter advice."
}}

The confidence value must be an integer from 0 to 100.

CV:

{cv_text}
"""

    feedback = """
<h2>AI is temporarily unavailable.</h2>
<p>Please wait a few seconds and try again.</p>
"""

    recruiter_review = {
        "verdict": "Review unavailable",
        "confidence": 0,
        "strengths": [
            "The recruiter assessment could not be generated.",
        ],
        "concerns": [
            "Please try the review again in a few moments.",
        ],
        "advice": (
            "Your CV score was still calculated successfully, "
            "but the recruiter assessment is temporarily unavailable."
        ),
    }

    try:
        review_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": review_prompt,
                }
            ],
            max_tokens=700,
        )

        feedback = markdown.markdown(
            review_response.choices[0].message.content,
            extensions=["extra"],
        )

        recruiter_response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": recruiter_prompt,
                }
            ],
            max_tokens=550,
            response_format={
                "type": "json_object",
            },
        )

        recruiter_review = json.loads(
            recruiter_response.choices[0].message.content
        )

        recruiter_review["confidence"] = max(
            0,
            min(
                100,
                int(recruiter_review.get("confidence", 0)),
            ),
        )

        recruiter_review.setdefault(
            "verdict",
            "Possible Shortlist",
        )
        recruiter_review.setdefault(
            "strengths",
            [],
        )
        recruiter_review.setdefault(
            "concerns",
            [],
        )
        recruiter_review.setdefault(
            "advice",
            "Review the detailed feedback before applying.",
        )

    except Exception as error:
        app.logger.exception(
            "AI CV review failed: %s",
            error,
        )

    saved_review = Review(
        score=overall_score,
        feedback=feedback,
        user_id=current_user.id,
    )

    db.session.add(saved_review)
    db.session.commit()

    return render_template(
        "results.html",
        feedback=feedback,
        overall_score=overall_score,
        score_breakdown=score_breakdown,
        recruiter_review=recruiter_review,
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name:
            error = "Please enter your name."

        elif not email:
            error = "Please enter your email address."

        elif len(password) < 8:
            error = "Your password must contain at least 8 characters."

        elif User.query.filter_by(email=email).first():
            error = "An account already exists with that email address."

        else:
            new_user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(
                    password,
                    method="pbkdf2:sha256",
                ),
            )

            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for("login"))

    return render_template(
        "register.html",
        error=error,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        error = "Incorrect email address or password."

    return render_template(
        "login.html",
        error=error,
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/history")
@login_required
def history():
    reviews = (
        Review.query
        .filter_by(user_id=current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )

    return render_template(
        "history.html",
        reviews=reviews,
    )


@app.route("/history/<int:review_id>")
@login_required
def view_review(review_id):
    review = Review.query.filter_by(
        id=review_id,
        user_id=current_user.id,
    ).first_or_404()

    return render_template(
        "saved_review.html",
        review=review,
    )


@app.route("/job-match", methods=["GET", "POST"])
@login_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def job_match():
    if request.method == "GET":
        return render_template("job_match.html")

    cv_text = request.form.get("cv_text", "").strip()
    job_description = request.form.get("job_description", "").strip()

    if not cv_text or not job_description:
        return render_template(
            "job_match.html",
            error="Please provide both your CV and the job description.",
        )

    prompt = f"""
You are an expert recruitment consultant.

Compare the candidate's CV with the job description.

Do not invent qualifications, experience, or achievements.

Use exactly these headings:

# 🎯 Match Assessment
Give a realistic match percentage from 0 to 100 and explain it briefly.

# ✅ Matching Strengths
Give four bullet points showing where the CV matches the role.

# ⚠️ Missing Skills
List skills requested by the employer that are missing from the CV.

# 🔑 Missing Keywords
List important ATS keywords from the job description that do not appear in the CV.

# ✍️ Recommended CV Changes
Give five specific, honest changes the candidate should make.

# 🎤 Likely Interview Questions
Generate five questions based on the role and CV.

# 🚀 Final Recommendation
Give a short practical summary.

CV:
{cv_text}

JOB DESCRIPTION:
{job_description}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=900,
        )

        match_feedback = markdown.markdown(
            response.choices[0].message.content,
            extensions=["extra"],
        )

    except Exception:
        match_feedback = """
<h2>AI is temporarily unavailable.</h2>
<p>Please wait a few seconds and try again.</p>
"""

    return render_template(
        "job_match_results.html",
        match_feedback=match_feedback,
    )


@app.route("/cover-letter", methods=["GET", "POST"])
@login_required
@pro_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def cover_letter():
    if request.method == "GET":
        return render_template("cover_letter.html")

    cv = request.form.get("cv", "").strip()
    job = request.form.get("job", "").strip()

    if not cv or not job:
        return render_template(
            "cover_letter.html",
            error="Please complete both fields.",
        )

    prompt = f"""
You are an expert recruitment consultant.

Write a professional cover letter.

Requirements:

- One page only
- Professional tone
- Personalised using the CV
- Personalised using the job description
- Do not invent experience

CV:

{cv}

JOB DESCRIPTION:

{job}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=900,
        )

        letter = markdown.markdown(
            response.choices[0].message.content,
            extensions=["extra"],
        )

    except Exception:
        letter = """
<h2>AI is temporarily unavailable.</h2>
<p>Please wait a few seconds and try again.</p>
"""

    return render_template(
    "cover_letter_results.html",
    letter=letter,
)

@app.route("/application-readiness", methods=["GET", "POST"])
@login_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def application_readiness():

    if request.method == "GET":
        return render_template("application_readiness.html")

    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    cv = request.form.get("cv", "").strip()
    job_description = request.form.get("job_description", "").strip()

    if not cv or not job_description:
        return render_template(
            "application_readiness.html",
            error="Please complete every field."
        )

    cv_score, breakdown = score_cv(cv)

    job_match_score, matching_keywords, missing_keywords = calculate_job_match(
        cv,
        job_description,
    )

    evidence_score = calculate_evidence_score(cv)

    readiness_score = calculate_readiness_score(
        cv_score,
        job_match_score,
        evidence_score,
    )

    status = get_readiness_status(readiness_score)

    return render_template(
        "application_results.html",
        job_title=job_title,
        company=company,
        cv_score=cv_score,
        job_match_score=job_match_score,
        evidence_score=evidence_score,
        readiness_score=readiness_score,
        status=status,
        matching_keywords=matching_keywords,
        missing_keywords=missing_keywords,
        breakdown=breakdown,
    )

@app.route("/rewrite", methods=["GET", "POST"])
@login_required
@pro_required
@limiter.limit(
    "1000 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def rewrite():
    if request.method == "GET":
        return render_template("rewrite.html")

    cv = request.form.get("cv", "").strip()

    if not cv:
        return render_template(
            "rewrite.html",
            error="Please paste your CV."
        )

    improved = improve_cv(cv)

    improved = markdown.markdown(
        improved,
        extensions=["extra"]
    )

    return render_template(
        "rewrite_results.html",
        improved=improved
    )
@app.route("/application-builder", methods=["GET", "POST"])
@login_required
@pro_required
def application_builder():
    if request.method == "GET":
        return render_template("application_builder.html")

    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    cv = request.form.get("cv", "").strip()
    job_description = request.form.get("job_description", "").strip()

    if not cv or not job_description:
        return render_template(
            "application_builder.html",
            error="Please complete every field."
        )

    # CV Score
    cv_score, breakdown = score_cv(cv)

    # Job Match
    job_match_score, matching_keywords, missing_keywords = calculate_job_match(
        cv,
        job_description,
    )

    # Evidence
    evidence_score = calculate_evidence_score(cv)

    # Readiness
    readiness_score = calculate_readiness_score(
        cv_score,
        job_match_score,
        evidence_score,
    )

    status = get_readiness_status(readiness_score)

    # Rewrite
    rewritten_cv = improve_cv(cv)

    rewritten_cv = markdown.markdown(
        rewritten_cv,
        extensions=["extra"]
    )

    return render_template(
        "application_builder_results.html",
        job_title=job_title,
        company=company,
        cv_score=cv_score,
        job_match_score=job_match_score,
        evidence_score=evidence_score,
        readiness_score=readiness_score,
        status=status,
        matching_keywords=matching_keywords,
        missing_keywords=missing_keywords,
        rewritten_cv=rewritten_cv,
        breakdown=breakdown,
    )    
@app.route("/interview", methods=["GET", "POST"])
@login_required
@pro_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def interview():
    if request.method == "GET":
        return render_template("interview.html")

    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    cv = request.form.get("cv", "").strip()

    if not job_title or not company or not cv:
        return render_template(
            "interview.html",
            error="Please complete every field.",
        )

    prompt = f"""
You are a professional interviewer.

Generate one realistic interview question for this role.

Job title: {job_title}
Company: {company}

Candidate CV or experience:
{cv}

Return only the question.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=180,
        )

        question = response.choices[0].message.content.strip()

    except Exception:
        return render_template(
            "interview.html",
            error="The AI is temporarily unavailable. Please try again.",
        )

    return render_template(
        "interview_question.html",
        job_title=job_title,
        company=company,
        cv=cv,
        question=question,
    )


@app.route("/interview-feedback", methods=["POST"])
@login_required
@pro_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def interview_feedback():
    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    cv = request.form.get("cv", "").strip()
    question = request.form.get("question", "").strip()
    answer = request.form.get("answer", "").strip()

    if not answer:
        return redirect(url_for("interview"))

    prompt = f"""
You are an expert interview coach.

Evaluate the candidate's answer honestly.

Role: {job_title}
Company: {company}

Candidate background:
{cv}

Question:
{question}

Candidate answer:
{answer}

Use exactly these headings:

# Overall Score
Give a score out of 100.

# What Was Strong
Give three bullet points.

# What Needs Improvement
Give three bullet points.

# Better Structure
Show how the answer could be structured using STAR where appropriate.

# Improved Example Answer
Write a stronger answer without inventing experience.

# Final Coaching Advice
Give one short paragraph.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=850,
        )

        feedback = markdown.markdown(
            response.choices[0].message.content,
            extensions=["extra"],
        )

    except Exception:
        feedback = """
<h2>AI is temporarily unavailable.</h2>
<p>Please wait a few seconds and try again.</p>
"""

    return render_template(
        "interview_feedback.html",
        feedback=feedback,
    )
@app.route("/jobs", methods=["GET", "POST"])
@login_required
def jobs():
    if request.method == "POST":
        job_title = request.form.get("job_title", "").strip()
        company = request.form.get("company", "").strip()
        job_url = request.form.get("job_url", "").strip()
        notes = request.form.get("notes", "").strip()

        if job_title and company:
            application = JobApplication(
                job_title=job_title,
                company=company,
                job_url=job_url or None,
                notes=notes or None,
                user_id=current_user.id,
            )

            db.session.add(application)
            db.session.commit()

            return redirect(url_for("jobs"))

    applications = (
        JobApplication.query
        .filter_by(user_id=current_user.id)
        .order_by(JobApplication.created_at.desc())
        .all()
    )

    return render_template(
        "jobs.html",
        applications=applications,
    )


@app.route("/jobs/<int:job_id>/status", methods=["POST"])
@login_required
def update_job_status(job_id):
    application = JobApplication.query.filter_by(
        id=job_id,
        user_id=current_user.id,
    ).first_or_404()

    allowed_statuses = {
        "Saved",
        "Applied",
        "Interview",
        "Offer",
        "Rejected",
    }

    new_status = request.form.get("status", "")

    if new_status in allowed_statuses:
        application.status = new_status
        db.session.commit()

    return redirect(url_for("jobs"))

@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
@login_required
def delete_job(job_id):
    application = JobApplication.query.filter_by(
        id=job_id,
        user_id=current_user.id,
    ).first_or_404()

    db.session.delete(application)
    db.session.commit()

    return redirect(url_for("jobs"))

@app.route("/recruiter-review", methods=["GET", "POST"])
@login_required
@pro_required
@limiter.limit(
    "3 per day",
    exempt_when=lambda: (
        current_user.is_authenticated
        and current_user.subscription == "Pro"
    ),
)
def recruiter_review():
    if request.method == "GET":
        return render_template("recruiter_review.html")

    job_title = request.form.get("job_title", "").strip()
    company = request.form.get("company", "").strip()
    cv = request.form.get("cv", "").strip()
    job_description = request.form.get("job_description", "").strip()

    if not job_title or not company or not cv or not job_description:
        return render_template(
            "recruiter_review.html",
            error="Please complete every field.",
        )

    prompt = f"""
You are a senior UK recruiter reviewing a real job application.

Assess the candidate honestly using only the evidence in their CV.
Do not invent experience, qualifications, skills, achievements, or outcomes.
Do not guarantee that the candidate will receive an interview.

Job title:
{job_title}

Company:
{company}

Candidate CV:
{cv}

Job description:
{job_description}

Use exactly these headings:

# Recruiter's Decision
Choose one:
- Invite to Interview
- Possible Interview
- Unlikely to Interview

Give a short explanation.

# Confidence
Give a percentage from 0 to 100 showing confidence in your assessment.

# First Impression
Explain what a recruiter would notice during an initial scan.

# Strongest Evidence
Give four bullet points grounded in the CV.

# Main Concerns
Give four bullet points.

# ATS and Keyword Fit
Explain how well the CV matches the vacancy and identify important missing keywords.

# Questions I Would Ask
Generate five realistic interview questions.

# Changes Before Applying
Give five specific and honest changes.

# Recruiter's Notes
Write a short note as though it were being sent to the hiring manager.

Finish by clearly stating that this is AI guidance, not a hiring guarantee.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=1100,
        )

        recruiter_feedback = markdown.markdown(
            response.choices[0].message.content,
            extensions=["extra"],
        )

    except Exception:
        recruiter_feedback = """
<h2>AI is temporarily unavailable.</h2>
<p>Please wait a few seconds and try again.</p>
"""

    return render_template(
        "recruiter_results.html",
        recruiter_feedback=recruiter_feedback,
        job_title=job_title,
        company=company,
    )

@app.errorhandler(429)
def rate_limit_reached(error):
    return render_template(
        "limit_reached.html",
        message="You have reached today's free AI usage limit. Please try again tomorrow or upgrade when Pro becomes available.",
    ), 429
@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/upgrade")
@login_required
def upgrade():

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1,
                }
            ],
            customer_email=current_user.email,
            client_reference_id=str(current_user.id),
            success_url=url_for(
                "upgrade_success",
                _external=True,
            ),
            cancel_url=url_for(
                "dashboard",
                _external=True,
            ),
        )

        return redirect(
            checkout_session.url,
            code=303,
        )

    except Exception as e:
        return str(e)


@app.route("/upgrade-success")
@login_required
def upgrade_success():

    return render_template(
        "upgrade_success.html"
    )
@app.route("/webhook", methods=["POST"])
def stripe_webhook():

    payload = request.data
    signature = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            STRIPE_WEBHOOK_SECRET,
        )

    except ValueError:
        return "Invalid payload", 400

    except stripe.error.SignatureVerificationError:
        return "Invalid signature", 400

    if event["type"] == "checkout.session.completed":

        session = event["data"]["object"]

        print("Event:", event["type"])
        print("User ID:", session.client_reference_id)

        user_id = session.client_reference_id

        if user_id:

            user = db.session.get(User, int(user_id))

            if user:

                user.subscription = "Pro"
                user.stripe_customer_id = session.customer
                user.stripe_subscription_id = session.subscription

                db.session.commit()

    return "", 200
@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)