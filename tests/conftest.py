import os
import sys

import pytest

# Make the project root importable.
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    ),
)

from app import app as flask_app
from extensions import db


@pytest.fixture
def app():
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )

    with flask_app.app_context():
        db.create_all()

        yield flask_app

        db.session.remove()
        db.drop_all()