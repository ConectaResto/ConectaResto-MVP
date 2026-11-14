from app.extensions import db
from app.models import Rol, Usuario


def list_users():
    return db.session.execute(db.select(Usuario).order_by(Usuario.username)).scalars().all()


def get_user_by_id(user_id):
    return db.session.get(Usuario, user_id)


def user_exists_by_username(username, exclude_id=None):
    query = db.select(Usuario).filter_by(username=username)
    if exclude_id is not None:
        query = query.filter(Usuario.id != exclude_id)
    return db.session.execute(query).scalar_one_or_none() is not None


def user_exists_by_email(email, exclude_id=None):
    query = db.select(Usuario).filter_by(email=email)
    if exclude_id is not None:
        query = query.filter(Usuario.id != exclude_id)
    return db.session.execute(query).scalar_one_or_none() is not None


def get_rol_by_name(name):
    return db.session.execute(db.select(Rol).filter_by(name=name)).scalar_one_or_none()


def ensure_roles():
    roles_data = [
        ("ADMIN", "Administrador del sistema"),
        ("WAITER", "Mesero de sala"),
        ("KITCHEN", "Personal de cocina"),
        ("CASHIER", "Cajero de punto de venta"),
    ]
    for name, description in roles_data:
        rol = get_rol_by_name(name)
        if rol is None:
            rol = Rol(name=name, description=description)
            db.session.add(rol)
    db.session.commit()


def create_user(username, email, password, rol_name):
    if user_exists_by_username(username):
        return None, "username_duplicado"
    if user_exists_by_email(email):
        return None, "email_duplicado"
    rol = get_rol_by_name(rol_name)
    if rol is None:
        return None, "rol_no_encontrado"
    user = Usuario(username=username, email=email, rol_id=rol.id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user, None


def update_user(user, data):
    username = data.get("username")
    email = data.get("email")
    rol_name = data.get("rol")
    password = data.get("password")

    if username is not None:
        if not isinstance(username, str) or not username:
            return "username_invalido"
        if user_exists_by_username(username, exclude_id=user.id):
            return "username_duplicado"
        user.username = username

    if email is not None:
        if not isinstance(email, str) or not email:
            return "email_invalido"
        if user_exists_by_email(email, exclude_id=user.id):
            return "email_duplicado"
        user.email = email

    if rol_name is not None:
        if not isinstance(rol_name, str) or not rol_name:
            return "rol_invalido"
        rol = get_rol_by_name(rol_name)
        if rol is None:
            return "rol_no_encontrado"
        if user.rol.name == "ADMIN" and rol.name != "ADMIN" and user.is_active:
            active_admins = db.session.execute(
                db.select(Usuario).join(Rol).filter(Rol.name == "ADMIN", Usuario.is_active == True)
            ).scalars().all()
            if len(active_admins) <= 1:
                return "ultimo_admin_activo"
        user.rol_id = rol.id

    if password is not None:
        if not isinstance(password, str) or not password:
            return "password_invalido"
        user.set_password(password)

    db.session.commit()
    return None


def deactivate_user(user, actor):
    if user.id == actor.id:
        return "autodesactivacion_prohibida"
    if user.rol.name == "ADMIN" and user.is_active:
        active_admins = db.session.execute(
            db.select(Usuario).join(Rol).filter(Rol.name == "ADMIN", Usuario.is_active == True)
        ).scalars().all()
        if len(active_admins) <= 1:
            return "ultimo_admin_activo"
    user.is_active = False
    db.session.commit()
    return None


def count_active_admins():
    return db.session.execute(
        db.select(Usuario).join(Rol).filter(Rol.name == "ADMIN", Usuario.is_active == True)
    ).scalars().all()


def create_admin_user(username, email, password):
    ensure_roles()
    existing = db.session.execute(db.select(Usuario).filter_by(username=username)).scalar_one_or_none()
    if existing:
        return existing
    rol_admin = get_rol_by_name("ADMIN")
    if rol_admin is None:
        rol_admin = Rol(name="ADMIN", description="Administrador del sistema")
        db.session.add(rol_admin)
        db.session.commit()
    user = Usuario(username=username, email=email, rol_id=rol_admin.id)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user
