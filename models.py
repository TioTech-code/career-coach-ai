from extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    name = db.Column(
        db.String(100),
        nullable=False,
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False,
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False,
    )


class Review(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    score = db.Column(
        db.Integer,
        nullable=False,
    )

    feedback = db.Column(
        db.Text,
        nullable=False,
    )

    created_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False,
    )