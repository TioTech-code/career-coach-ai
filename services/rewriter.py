from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def improve_cv(cv_text):

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