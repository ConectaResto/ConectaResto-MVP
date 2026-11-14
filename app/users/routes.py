from flask import Blueprint, request

from app.extensions import db
from app.auth.decorators import login_required, roles_required
from app.auth.service import current_user
from app.common.responses import error_response, success_response
from app.users.service import (
    count_active_admins,
    create_user,
    deactivate_user,
    get_user_by_id,
    list_users,
    update_user,
)

users_bp = Blueprint("users", __name__, url_prefix="/users")


def _serialize_user(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "rol": user.rol.name,
        "is_active": user.is_active,
    }


@users_bp.get("")
@login_required
@roles_required("ADMIN")
def list_users_endpoint():
    users = list_users()
    return success_response({"users": [_serialize_user(u) for u in users]})


@users_bp.get("/<int:user_id>")
@login_required
@roles_required("ADMIN")
def get_user_endpoint(user_id):
    user = get_user_by_id(user_id)
    if user is None:
        return error_response("Usuario no encontrado", 404)
    return success_response(_serialize_user(user))


@users_bp.post("")
@login_required
@roles_required("ADMIN")
def create_user_endpoint():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("Cuerpo JSON inválido", 400)

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    rol_name = data.get("rol")

    if not isinstance(username, str) or not username:
        return error_response("username es requerido", 400)
    if not isinstance(email, str) or not email:
        return error_response("email es requerido", 400)
    if not isinstance(password, str) or not password:
        return error_response("password es requerido", 400)
    if not isinstance(rol_name, str) or not rol_name:
        return error_response("rol es requerido", 400)

    user, err = create_user(username, email, password, rol_name)
    if err == "username_duplicado":
        return error_response("El username ya está en uso", 409)
    if err == "email_duplicado":
        return error_response("El email ya está en uso", 409)
    if err == "rol_no_encontrado":
        return error_response("Rol no encontrado", 404)
    return success_response(_serialize_user(user), status_code=201)


@users_bp.patch("/<int:user_id>")
@login_required
@roles_required("ADMIN")
def update_user_endpoint(user_id):
    user = get_user_by_id(user_id)
    if user is None:
        return error_response("Usuario no encontrado", 404)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error_response("Cuerpo JSON inválido", 400)

    err = update_user(user, data)
    if err == "username_invalido":
        return error_response("username inválido", 400)
    if err == "username_duplicado":
        return error_response("El username ya está en uso", 409)
    if err == "email_invalido":
        return error_response("email inválido", 400)
    if err == "email_duplicado":
        return error_response("El email ya está en uso", 409)
    if err == "rol_invalido":
        return error_response("rol inválido", 400)
    if err == "rol_no_encontrado":
        return error_response("Rol no encontrado", 404)
    if err == "ultimo_admin_activo":
        return error_response("No se puede cambiar el rol del último ADMIN activo", 409)
    if err == "password_invalido":
        return error_response("password inválido", 400)
    db.session.commit()
    return success_response(_serialize_user(user))


@users_bp.delete("/<int:user_id>")
@login_required
@roles_required("ADMIN")
def deactivate_user_endpoint(user_id):
    actor = current_user()
    user = get_user_by_id(user_id)
    if user is None:
        return error_response("Usuario no encontrado", 404)

    err = deactivate_user(user, actor)
    if err == "autodesactivacion_prohibida":
        return error_response("No se puede desactivar a sí mismo", 409)
    if err == "ultimo_admin_activo":
        return error_response("No se puede desactivar al último ADMIN activo", 409)
    return success_response(message="Usuario desactivado")
