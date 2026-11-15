import time

import pytest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import Rol, Usuario, Mesa, Servicio, Product, Category, Pedido, DetallePedido, Pago


@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _crear_usuario(app, username, email, rol_nombre, password="testpass123"):
    """Crea un usuario con el rol dado dentro del contexto de app."""
    with app.app_context():
        rol = db.session.execute(
            db.select(Rol).filter_by(name=rol_nombre)
        ).scalar_one_or_none()
        if rol is None:
            rol = Rol(name=rol_nombre, description=f"Rol {rol_nombre}")
            db.session.add(rol)
            db.session.commit()

        usuario = Usuario(
            username=username,
            email=email,
            rol_id=rol.id,
        )
        usuario.set_password(password)
        db.session.add(usuario)
        db.session.commit()
        return usuario


def _autenticar_en_sesion(client, app, username="cajero1", rol_nombre="CASHIER"):
    """Establece la sesión de usuario directamente para pruebas."""
    with client.session_transaction() as sess:
        with app.app_context():
            usuario = db.session.execute(
                db.select(Usuario).filter_by(username=username)
            ).scalar_one_or_none()
            if usuario is None:
                _crear_usuario(app, username, f"{username}@test.com", rol_nombre)
                usuario = db.session.execute(
                    db.select(Usuario).filter_by(username=username)
                ).scalar_one()
        sess["user_id"] = usuario.id
        sess["authenticated_at"] = time.time()
        sess.permanent = True
        return usuario.id


def _crear_servicio_activo(app, mesa_numero=1, abierto_por_id=1, estado="ACTIVO"):
    """Crea un servicio activo para pruebas."""
    with app.app_context():
        mesa = db.session.execute(
            db.select(Mesa).filter_by(numero=mesa_numero)
        ).scalar_one_or_none()
        if mesa is None:
            mesa_estado = "OCUPADA" if estado == "ACTIVO" else "DISPONIBLE"
            mesa = Mesa(numero=mesa_numero, estado=mesa_estado, public_token="token_test")
            db.session.add(mesa)
            db.session.commit()
        elif estado == "ACTIVO":
            mesa.estado = "OCUPADA"
            db.session.commit()

        servicio = Servicio(
            mesa_id=mesa.id,
            abierto_por_id=abierto_por_id,
            estado=estado,
        )
        db.session.add(servicio)
        db.session.commit()
        return servicio.id


def _crear_pedido_en_servicio(app, servicio_id, estado="ENTREGADO", estado_preparacion="NO_ENVIADO"):
    """Crea un pedido con un detalle para un servicio."""
    with app.app_context():
        categoria = db.session.execute(
            db.select(Category).filter_by(name="Bebidas")
        ).scalar_one_or_none()
        if categoria is None:
            categoria = Category(name="Bebidas", description="Bebidas")
            db.session.add(categoria)
            db.session.commit()

        producto = db.session.execute(
            db.select(Product).filter_by(name="Refresco", categoria_id=categoria.id)
        ).scalar_one_or_none()
        if producto is None:
            producto = Product(
                name="Refresco",
                description="Refresco de cola",
                price=2500,
                categoria_id=categoria.id,
                is_available=True,
            )
            db.session.add(producto)
            db.session.commit()

        pedido = Pedido(
            servicio_id=servicio_id,
            origen="MESERO",
            estado=estado,
            estado_preparacion=estado_preparacion,
        )
        db.session.add(pedido)
        db.session.commit()

        detalle = DetallePedido(
            pedido_id=pedido.id,
            producto_id=producto.id,
            cantidad=2,
            precio_unitario=producto.price,
        )
        db.session.add(detalle)
        db.session.commit()
        return pedido.id


class TestCashierFrontend:
    """Pruebas para el panel de caja (CASHIER)."""

    def test_cashier_acceso_autenticado(self, app, client):
        """Un usuario CASHIER autenticado puede acceder a /cashier."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        response = client.get("/cashier", follow_redirects=True)
        assert response.status_code == 200

    def test_cashier_sin_autenticacion_redirige_a_login(self, app, client):
        """Un usuario no autenticado no puede acceder a /cashier."""
        response = client.get("/cashier", follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_admin_no_puede_acceder_a_cashier(self, app, client):
        """Un usuario ADMIN no puede acceder al panel de caja."""
        _crear_usuario(app, "admin1", "admin1@test.com", "ADMIN")
        _autenticar_en_sesion(client, app, "admin1", "ADMIN")

        response = client.get("/cashier", follow_redirects=True)
        assert response.status_code == 403

    def test_waiter_no_puede_acceder_a_cashier(self, app, client):
        """Un usuario WAITER no puede acceder al panel de caja."""
        _crear_usuario(app, "mesero1", "mesero1@test.com", "WAITER")
        _autenticar_en_sesion(client, app, "mesero1", "WAITER")

        response = client.get("/cashier", follow_redirects=True)
        assert response.status_code == 403

    def test_kitchen_no_puede_acceder_a_cashier(self, app, client):
        """Un usuario KITCHEN no puede acceder al panel de caja."""
        _crear_usuario(app, "cocinero1", "cocinero1@test.com", "KITCHEN")
        _autenticar_en_sesion(client, app, "cocinero1", "KITCHEN")

        response = client.get("/cashier", follow_redirects=True)
        assert response.status_code == 403

    def test_listar_servicios_activos_cashier(self, app, client):
        """Un CASHIER puede listar servicios activos."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        _crear_servicio_activo(app, mesa_numero=1)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response = client.get(
            "/servicios?estado=ACTIVO",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "data" in data
        servicios = data["data"]
        assert any(s["estado"] == "ACTIVO" for s in servicios)

    def test_obtener_servicio_por_id_cashier(self, app, client):
        """Un CASHIER puede obtener los detalles de un servicio."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        servicio_id = _crear_servicio_activo(app, mesa_numero=5)
        _crear_pedido_en_servicio(app, servicio_id)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response = client.get(
            f"/servicios/{servicio_id}",
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["id"] == servicio_id
        assert data["data"]["estado"] == "ACTIVO"
        assert "pedidos" in data["data"]
        assert len(data["data"]["pedidos"]) >= 1

    def test_pago_simulado_cashier(self, app, client):
        """Un CASHIER puede registrar pago simulado de un servicio."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        servicio_id = _crear_servicio_activo(app, mesa_numero=3)
        _crear_pedido_en_servicio(app, servicio_id)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response = client.post(
            f"/servicios/{servicio_id}/pago-simulado",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert "data" in data
        assert data["data"]["pago"] is not None
        assert data["data"]["pago"]["importe"] is not None

    def test_pago_simulado_sin_pedidos(self, app, client):
        """No se puede pagar un servicio sin pedidos."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        servicio_id = _crear_servicio_activo(app, mesa_numero=7)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response = client.post(
            f"/servicios/{servicio_id}/pago-simulado",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code in (400, 409)

    def test_cerrar_servicio_despues_de_pago(self, app, client):
        """Un CASHIER puede cerrar un servicio después de pagar."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        servicio_id = _crear_servicio_activo(app, mesa_numero=9)
        _crear_pedido_en_servicio(app, servicio_id)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response_pago = client.post(
            f"/servicios/{servicio_id}/pago-simulado",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response_pago.status_code == 201

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response_cierre = client.post(
            f"/servicios/{servicio_id}/cerrar",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response_cierre.status_code == 200
        data = response_cierre.get_json()
        assert data["data"]["estado"] == "CERRADO"

    def test_cerrar_servicio_sin_pago_falla(self, app, client):
        """No se puede cerrar un servicio sin pago previo."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        servicio_id = _crear_servicio_activo(app, mesa_numero=11)
        _crear_pedido_en_servicio(app, servicio_id)

        csrf_token = client.get("/auth/csrf").get_json()["data"]["csrf_token"]
        response = client.post(
            f"/servicios/{servicio_id}/cerrar",
            json={},
            headers={"X-CSRF-Token": csrf_token},
        )
        assert response.status_code in (400, 409)

    def test_obtener_csrf_token(self, app, client):
        """El endpoint CSRF devuelve un token válido."""
        response = client.get("/auth/csrf")
        assert response.status_code == 200
        data = response.get_json()
        assert "csrf_token" in data["data"]

    def test_cashier_template_tiene_elementos_para_interacciones_js(self, app, client):
        """El template de caja contiene los elementos DOM que el JavaScript requiere."""
        _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
        _autenticar_en_sesion(client, app, "cajero1", "CASHIER")

        response = client.get("/cashier", follow_redirects=True)
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Elementos que el JS consulta por id
        assert 'id="servicios-grid"' in html
        assert 'id="sin-servicios"' in html
        assert 'id="detalle-servicio"' in html
        assert 'id="mensaje-error"' in html
        assert 'id="tabla-pedidos-body"' in html
        assert 'id="btn-pagar-simulado"' in html
        assert 'id="btn-cerrar-servicio"' in html
        assert 'id="detalle-servicio-id"' in html
        assert 'id="detalle-servicio-mesa"' in html
        assert 'id="detalle-servicio-estado"' in html
        assert 'id="detalle-total-pagar"' in html

        # Meta tag CSRF que el JS lee para el token
        assert 'name="csrf-token"' in html

        # Script del frontend de caja
        assert 'js/cashier.js' in html
