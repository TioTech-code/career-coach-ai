import os
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite:///career_coach.db",
    )

    # Some providers use the older postgres:// prefix.
    if database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    return database_url


class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-secret-key",
    )

    SQLALCHEMY_DATABASE_URI = get_database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = "uploads"