import time

from flask import Blueprint, request, session

from app.auth.csrf import csrf_token
from app.auth.decorators import login_required
from app.auth.service import authenticate, current_user, public_user
from app.common.responses import error_response, success_response


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.after_request
def prevent_caching(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@auth_bp.get("/csrf")
def csrf():
    return success_response({"csrf_token": csrf_token()})


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(
        not isinstance(data.get(key), str) or not data[key]
        for key in ("username", "password")
    ):
        return error_response("Se requieren username y password", 400)
    user = authenticate(data["username"], data["password"])
    if user is None:
        return error_response("Credenciales invalidas", 401)
    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["authenticated_at"] = time.time()
    csrf_token()
    return success_response(public_user(user))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return success_response(message="Sesion cerrada")


@auth_bp.get("/me")
@login_required
def me():
    return success_response(public_user(current_user()))
