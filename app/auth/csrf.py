import hmac
import secrets

from flask import g, request, session

from app.common.responses import error_response


# Central allowlist of exact Flask endpoint names. Add only approved public routes.
CSRF_EXEMPT_ENDPOINTS = frozenset()


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def protect_csrf():
    """Require CSRF for unsafe requests, except explicitly approved endpoints."""
    # Tests and CLI callers may keep an application context across requests.
    g.pop("auth_user", None)
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    if request.endpoint in CSRF_EXEMPT_ENDPOINTS:
        return None
    expected = session.get("csrf_token")
    supplied = request.headers.get("X-CSRF-Token")
    if (not isinstance(expected, str) or not isinstance(supplied, str)
            or not hmac.compare_digest(expected.encode(), supplied.encode())):
        return error_response("Token CSRF invalido", 400)
