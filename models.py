from extensions import db
from flask_login import UserMixin


class User(UserMixin, db.Model):
    subscription = db.Column(
    db.String(20),
    default="Free",
    nullable=False,
)

stripe_customer_id = db.Column(
    db.String(255),
    nullable=True,
)

stripe_subscription_id = db.Column(
    db.String(255),
    nullable=True,
)
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


class JobApplication(db.Model):
    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    job_title = db.Column(
        db.String(150),
        nullable=False,
    )

    company = db.Column(
        db.String(150),
        nullable=False,
    )

    status = db.Column(
        db.String(50),
        default="Saved",
        nullable=False,
    )

    job_url = db.Column(
        db.String(500),
        nullable=True,
    )

    notes = db.Column(
        db.Text,
        nullable=True,
    )

    applied_at = db.Column(
        db.DateTime,
        nullable=True,
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