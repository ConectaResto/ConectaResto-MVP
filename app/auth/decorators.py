from functools import wraps

from app.auth.service import current_user
from app.common.responses import error_response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return error_response("No autorizado", 401)
        return view(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user().rol.name not in roles:
                return error_response("Prohibido", 403)
            return view(*args, **kwargs)
        return wrapped
    return decorate
