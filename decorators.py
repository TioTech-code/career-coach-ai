from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def pro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.subscription != "Pro":
            flash(
                "🚀 This is a Pro feature. Upgrade to unlock all AI tools.",
                "info",
            )
            return redirect(url_for("pricing"))
        return f(*args, **kwargs)

    return decorated_function