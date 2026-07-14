from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()


def get_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY environment variable is not set."
        )

    return Groq(api_key=api_key)


def improve_cv(cv_text):

    client = get_client()

    prompt = f"""
You are one of the world's best CV writers.

Rewrite the CV.

Rules:

Never invent experience.

Never invent skills.

Never invent qualifications.

Improve wording only.

For every improvement use this format.

## Original

(original sentence)

## Improved

(improved version)

## Why

(short explanation)

CV:

{cv_text}
"""

    response = client.chat.completions.create(

        model="llama-3.1-8b-instant",

        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],

        max_tokens=1200,
    )

    return response.choices[0].message.content