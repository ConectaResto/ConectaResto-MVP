from flask import Blueprint, current_app, render_template, redirect, url_for

from app.auth.csrf import csrf_token as _csrf_token
from app.auth.service import current_user

frontend_bp = Blueprint("frontend", __name__, template_folder="../templates")


@frontend_bp.before_request
def _inject_csrf_global():
    current_app.jinja_env.globals["csrf_token"] = _csrf_token


def _require_auth():
    """Devuelve el usuario autenticado o None si no hay sesión."""
    return current_user()


def _require_role(rol_name):
    """Devuelve el usuario si está autenticado y tiene el rol, o None."""
    user = _require_auth()
    if user is None:
        return None
    if user.rol is None or user.rol.name != rol_name:
        return "wrong_role"
    return user


def _panel_cards(rol_name):
    """Tarjetas de funcionalidades por rol."""
    if rol_name == "ADMIN":
        return [
            {
                "title": "Usuarios",
                "desc": "Crear, editar y desactivar usuarios del sistema.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
            {
                "title": "Categorías",
                "desc": "Administrar categorías de productos.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
            {
                "title": "Productos",
                "desc": "Administrar productos del catálogo.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
            {
                "title": "Mesas",
                "desc": "Administrar mesas del salón.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
            {
                "title": "Pedidos",
                "desc": "Ver y gestionar pedidos del sistema.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
        ]
    if rol_name == "WAITER":
        return [
            {
                "title": "Mesas",
                "desc": "Ver servicios activos y abrir mesas.",
                "enabled": True,
                "url": url_for("frontend.waiter_mesas"),
                "btn_text": "Ver mesas",
            },
            {
                "title": "Pedidos",
                "desc": "Crear, autorizar y enviar pedidos a cocina.",
                "enabled": True,
                "url": url_for("frontend.waiter_pedidos"),
                "btn_text": "Gestionar pedidos",
            },
        ]
    if rol_name == "KITCHEN":
        return [
            {
                "title": "Pedidos",
                "desc": "Ver pedidos y actualizar preparación.",
                "enabled": True,
                "url": url_for("frontend.kitchen_pedidos"),
                "btn_text": "Ver pedidos",
            },
        ]
    if rol_name == "CASHIER":
        return [
            {
                "title": "Pedidos para cobrar",
                "desc": "Ver pedidos listos para registrar pago.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
            {
                "title": "Cierre de caja",
                "desc": "Realizar cierre de caja diario.",
                "enabled": False,
                "url": None,
                "btn_text": "Próximamente",
            },
        ]
    return []


_PANEL_TITLES = {
    "ADMIN": "Panel ADMIN",
    "WAITER": "Panel Mesero",
    "KITCHEN": "Panel Cocina",
    "CASHIER": "Panel Caja",
}


@frontend_bp.get("/")
def index():
    user = _require_auth()
    if user is not None:
        return redirect(url_for("frontend.panel", rol=user.rol.name.lower()))
    return render_template("index.html")


@frontend_bp.get("/login")
def login():
    user = _require_auth()
    if user is not None:
        return redirect(url_for("frontend.panel", rol=user.rol.name.lower()))
    return render_template("login.html", error=None)


@frontend_bp.get("/panel/<rol>")
def panel(rol):
    rol_upper = rol.upper()
    user = _require_role(rol_upper)
    if user == "wrong_role":
        return render_template("unauthorized.html", user=_require_auth()), 403
    if user is None:
        return render_template("login.html", error="Debes iniciar sesión para acceder a este panel.")
    return render_template(
        f"{rol}.html",
        panel_title=_PANEL_TITLES.get(rol_upper, "Panel"),
        user={"username": user.username, "rol": user.rol.name},
        cards=_panel_cards(rol_upper),
    )


@frontend_bp.get("/admin")
def admin():
    return redirect(url_for("frontend.panel", rol="admin"))


@frontend_bp.get("/waiter")
def waiter():
    return redirect(url_for("frontend.panel", rol="waiter"))


@frontend_bp.get("/kitchen")
def kitchen():
    return redirect(url_for("frontend.panel", rol="kitchen"))


@frontend_bp.get("/cashier")
def cashier():
    return redirect(url_for("frontend.panel", rol="cashier"))


@frontend_bp.get("/waiter/mesas")
def waiter_mesas():
    user = _require_role("WAITER")
    if user == "wrong_role":
        return render_template("unauthorized.html", user=_require_auth()), 403
    if user is None:
        return render_template("login.html", error="Debes iniciar sesión para acceder a este panel.")
    return render_template(
        "waiter/mesas.html",
        panel_title=_PANEL_TITLES["WAITER"],
        user={"username": user.username, "rol": user.rol.name},
    )


@frontend_bp.get("/waiter/pedidos")
def waiter_pedidos():
    user = _require_role("WAITER")
    if user == "wrong_role":
        return render_template("unauthorized.html", user=_require_auth()), 403
    if user is None:
        return render_template("login.html", error="Debes iniciar sesión para acceder a este panel.")
    return render_template(
        "waiter/pedidos.html",
        panel_title=_PANEL_TITLES["WAITER"],
        user={"username": user.username, "rol": user.rol.name},
    )


@frontend_bp.get("/kitchen/pedidos")
def kitchen_pedidos():
    user = _require_role("KITCHEN")
    if user == "wrong_role":
        return render_template("unauthorized.html", user=_require_auth()), 403
    if user is None:
        return render_template("login.html", error="Debes iniciar sesión para acceder a este panel.")
    return render_template(
        "kitchen/pedidos.html",
        panel_title=_PANEL_TITLES["KITCHEN"],
        user={"username": user.username, "rol": user.rol.name},
    )
