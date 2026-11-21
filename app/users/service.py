from decimal import Decimal

from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.users.models import Rol, Usuario


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

    if "is_active" in data and data["is_active"] is not True:
        return "is_active_invalido"
    changes = {}

    if username is not None:
        if not isinstance(username, str) or not username:
            return "username_invalido"
        if user_exists_by_username(username, exclude_id=user.id):
            return "username_duplicado"
        changes["username"] = username

    if email is not None:
        if not isinstance(email, str) or not email:
            return "email_invalido"
        if user_exists_by_email(email, exclude_id=user.id):
            return "email_duplicado"
        changes["email"] = email

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
        changes["rol_id"] = rol.id

    if password is not None:
        if not isinstance(password, str) or not password:
            return "password_invalido"
        user.set_password(password)

    if "is_active" in data:
        changes["is_active"] = True
    for field, value in changes.items():
        setattr(user, field, value)
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


def ensure_mesas():
    """Crea 5 mesas de demostración si no existen (idempotente por número)."""
    for numero in range(1, 6):
        mesa = db.session.execute(
            db.select(Mesa).filter_by(numero=numero)
        ).scalar_one_or_none()
        if mesa is None:
            mesa = Mesa(numero=numero, estado="DISPONIBLE")
            db.session.add(mesa)
    db.session.commit()


def ensure_categorias():
    """Crea 3 categorías de demostración si no existen (idempotente por nombre)."""
    categorias_data = [
        ("Bebidas", "Bebidas frías y calientes"),
        ("Comidas", "Platos principales"),
        ("Postres", "Dulces y postres"),
    ]
    for name, description in categorias_data:
        cat = db.session.execute(
            db.select(Category).filter_by(name=name)
        ).scalar_one_or_none()
        if cat is None:
            cat = Category(name=name, description=description)
            db.session.add(cat)
    db.session.commit()


def ensure_productos():
    """Crea productos con precios positivos si no existen (idempotente por nombre dentro de categoría)."""
    productos_data = [
        ("Bebidas", "Agua mineral", "Agua sin gas 500 ml", Decimal("1500.00")),
        ("Bebidas", "Refresco cola", "Refresco de cola 500 ml", Decimal("2500.00")),
        ("Bebidas", "Jugo de naranja", "Jugo natural 300 ml", Decimal("3000.00")),
        ("Comidas", "Hamburguesa", "Hamburguesa con queso", Decimal("8500.00")),
        ("Comidas", "Pizza", "Pizza familiar", Decimal("12000.00")),
        ("Comidas", "Ensalada", "Ensalada mixta", Decimal("6500.00")),
        ("Postres", "Flan", "Flan de vainilla", Decimal("3500.00")),
        ("Postres", "Helado", "Helado de chocolate", Decimal("4000.00")),
    ]
    for cat_name, name, description, price in productos_data:
        cat = db.session.execute(
            db.select(Category).filter_by(name=cat_name)
        ).scalar_one_or_none()
        if cat is None:
            continue
        prod = db.session.execute(
            db.select(Product).filter_by(name=name, categoria_id=cat.id)
        ).scalar_one_or_none()
        if prod is None:
            prod = Product(
                name=name,
                description=description,
                price=price,
                categoria_id=cat.id,
            )
            db.session.add(prod)
    db.session.commit()


def ensure_usuarios_operativos(password=None):
    """Crea usuarios operativos de demostración si no existen (idempotente por username)."""
    usuarios_data = [
        ("mesero1", "mesero1@conectaresto.test", "WAITER"),
        ("cajero1", "cajero1@conectaresto.test", "CASHIER"),
        ("cocinero1", "cocinero1@conectaresto.test", "KITCHEN"),
        ("admin1", "admin1@conectaresto.test", "ADMIN"),
    ]
    for username, email, rol_name in usuarios_data:
        existing = db.session.execute(
            db.select(Usuario).filter_by(username=username)
        ).scalar_one_or_none()
        if existing is None:
            rol = get_rol_by_name(rol_name)
            if rol is None:
                continue
            user = Usuario(username=username, email=email, rol_id=rol.id)
            if password:
                user.set_password(password)
            db.session.add(user)
    db.session.commit()


def seed_demo(password=None):
    """Ejecuta la siembra completa de datos de demostración (idempotente).

    Crea en orden: roles, mesas, categorías, productos y usuarios operativos.
    Nunca sobrescribe registros existentes.
    """
    ensure_roles()
    ensure_mesas()
    ensure_categorias()
    ensure_productos()
    ensure_usuarios_operativos(password=password)
