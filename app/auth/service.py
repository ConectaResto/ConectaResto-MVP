import time

from flask import g, session

from app.extensions import db
from app.users.models import Usuario


SESSION_SECONDS = 8 * 60 * 60


def public_user(user):
    return {"id": user.id, "username": user.username, "rol": user.rol.name}


def authenticate(username, password):
    user = db.session.execute(
        db.select(Usuario).filter_by(username=username)
    ).scalar_one_or_none()
    if user is None or not user.check_password(password) or not user.is_active:
        return None
    return user


def current_user():
    if "auth_user" not in g:
        user = None
        started = session.get("authenticated_at")
        user_id = session.get("user_id")
        now = time.time()
        if (type(started) in (int, float) and type(user_id) is int
                and 0 <= now - started < SESSION_SECONDS):
            user = db.session.get(Usuario, user_id)
            if user is not None and (not user.is_active or user.rol is None):
                user = None
        if user is None and user_id is not None:
            session.clear()
        g.auth_user = user
    return g.auth_user
