from flask import Flask, render_template, request
from groq import Groq
from dotenv import load_dotenv
from pypdf import PdfReader
from werkzeug.utils import secure_filename
from scoring import score_cv
import markdown
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/cv-review")
def cv_review():
    return render_template("cv_review.html")


@app.route("/review", methods=["POST"])
def review():

    cv_text = ""

    uploaded_file = request.files.get("cv_file")

    if uploaded_file and uploaded_file.filename:

        filename = secure_filename(uploaded_file.filename)

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        uploaded_file.save(filepath)

        reader = PdfReader(filepath)

        for page in reader.pages:

            text = page.extract_text()

            if text:
                cv_text += text + "\n"

    else:

        cv_text = request.form.get("cv", "")

    if not cv_text.strip():
        return "Please upload a PDF or paste your CV."

    overall_score, score_breakdown = score_cv(cv_text)

    prompt = f"""
You are an experienced professional CV reviewer.

IMPORTANT:
Do NOT give an overall score because the application already calculates one.

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

CV:

{cv_text}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=700
        )

        feedback = markdown.markdown(
            response.choices[0].message.content,
            extensions=["extra"]
        )

    except Exception:

        feedback = """
<h2>AI is temporarily unavailable.</h2>

<p>
Please wait a few seconds and try again.
</p>
"""

    return render_template(
        "results.html",
        feedback=feedback,
        overall_score=overall_score,
        score_breakdown=score_breakdown
    )


if __name__ == "__main__":
    app.run(debug=True)