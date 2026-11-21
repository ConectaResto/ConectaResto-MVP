from app.users.models import Rol, Usuario


def test_crear_roles_estandar(app):
    """Se pueden crear los cuatro roles definidos en el plan del MVP."""
    roles_data = [
        ("ADMIN", "Administrador del sistema"),
        ("WAITER", "Mesero de sala"),
        ("KITCHEN", "Personal de cocina"),
        ("CASHIER", "Cajero de punto de venta"),
    ]

    with app.app_context():
        from app.extensions import db

        for nombre, descripcion in roles_data:
            rol = Rol(name=nombre, description=descripcion)
            db.session.add(rol)

        db.session.commit()

        roles = db.session.query(Rol).order_by(Rol.name).all()
        assert len(roles) == 4

        nombres = [rol.name for rol in roles]
        assert "ADMIN" in nombres
        assert "WAITER" in nombres
        assert "KITCHEN" in nombres
        assert "CASHIER" in nombres


def test_rol_nombre_es_unico(app):
    """El nombre del rol debe ser único."""
    with app.app_context():
        from app.extensions import db

        rol1 = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol1)
        db.session.commit()

        rol2 = Rol(name="ADMIN", description="Duplicado")
        db.session.add(rol2)

        try:
            db.session.commit()
            assert False, "Debería haber fallado por rol duplicado"
        except Exception:
            db.session.rollback()


def test_crear_usuario_con_contrasena_encriptada(app):
    """Se puede crear un usuario y su contraseña se almacena como hash."""
    with app.app_context():
        from app.extensions import db

        rol_admin = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol_admin)
        db.session.commit()

        usuario = Usuario(
            username="mesero1",
            email="mesero1@conectaresto.com",
            rol_id=rol_admin.id,
        )
        usuario.set_password("ClaveSegura123")
        db.session.add(usuario)
        db.session.commit()

        assert usuario.id is not None
        assert usuario.username == "mesero1"
        assert usuario.email == "mesero1@conectaresto.com"
        assert usuario.password_hash != "ClaveSegura123"
        assert usuario.is_active is True


def test_verificar_contrasena_correcta(app):
    """check_password devuelve True con la contraseña correcta."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="WAITER", description="Mesero")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="mesero2",
            email="mesero2@conectaresto.com",
            rol_id=rol.id,
        )
        usuario.set_password("ClaveSegura123")
        db.session.commit()

        assert usuario.check_password("ClaveSegura123") is True


def test_verificar_contrasena_incorrecta(app):
    """check_password devuelve False con contraseña incorrecta."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="KITCHEN", description="Cocina")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="cocina1",
            email="cocina1@conectaresto.com",
            rol_id=rol.id,
        )
        usuario.set_password("ClaveSegura123")
        db.session.commit()

        assert usuario.check_password("ClaveIncorrecta") is False


def test_usuario_username_es_unico(app):
    """El username debe ser único."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="CASHIER", description="Cajero")
        db.session.add(rol)
        db.session.commit()

        u1 = Usuario(username="cajero1", email="cajero1@conectaresto.com", rol_id=rol.id)
        u1.set_password("Clave123")
        db.session.add(u1)
        db.session.commit()

        u2 = Usuario(username="cajero1", email="cajero2@conectaresto.com", rol_id=rol.id)
        u2.set_password("Clave123")
        db.session.add(u2)

        try:
            db.session.commit()
            assert False, "Debería haber fallado por username duplicado"
        except Exception:
            db.session.rollback()


def test_usuario_email_es_unico(app):
    """El email debe ser único."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()

        u1 = Usuario(username="admin1", email="admin@conectaresto.com", rol_id=rol.id)
        u1.set_password("Clave123")
        db.session.add(u1)
        db.session.commit()

        u2 = Usuario(username="admin2", email="admin@conectaresto.com", rol_id=rol.id)
        u2.set_password("Clave123")
        db.session.add(u2)

        try:
            db.session.commit()
            assert False, "Debería haber fallado por email duplicado"
        except Exception:
            db.session.rollback()


def test_usuario_tiene_relacion_con_rol(app):
    """Un usuario tiene una relación con su rol."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="admin1",
            email="admin1@conectaresto.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        assert usuario.rol is not None
        assert usuario.rol.name == "ADMIN"


def test_usuario_tiene_campos_base_model(app):
    """Usuario hereda id, created_at y updated_at de BaseModel."""
    with app.app_context():
        from app.extensions import db

        rol = Rol(name="ADMIN", description="Administrador")
        db.session.add(rol)
        db.session.commit()

        usuario = Usuario(
            username="testuser",
            email="test@conectaresto.com",
            rol_id=rol.id,
        )
        usuario.set_password("Clave123")
        db.session.add(usuario)
        db.session.commit()

        assert usuario.id is not None
        assert usuario.created_at is not None
        assert usuario.updated_at is not None