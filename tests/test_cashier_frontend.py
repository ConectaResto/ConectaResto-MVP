import time

import pytest
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.servicios.models import Pago, Servicio
from app.users.models import Rol, Usuario


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

@pytest.mark.parametrize("scenario", ["flow", "paid", "empty"])
def test_cashier_flujo_y_persistencia(app, client, scenario):
    _crear_usuario(app, "cajero1", "cajero1@test.com", "CASHIER")
    _autenticar_en_sesion(client, app)
    listado = "/servicios?estado=ACTIVO"
    if scenario == "empty":
        assert client.get(listado).json["data"] == []
        assert db.session.query(Pago).count() == 0
        assert db.session.query(Servicio).count() == 0
        return

    servicio_id = _crear_servicio_activo(app, mesa_numero=7)
    _crear_pedido_en_servicio(app, servicio_id)
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    headers = {"X-CSRF-Token": token}
    ruta = f"/servicios/{servicio_id}"
    if scenario == "flow":
        with app.app_context():
            db.session.add(Mesa(numero=8))
            db.session.commit()
        pendiente = _crear_servicio_activo(app, mesa_numero=8)
        _crear_pedido_en_servicio(app, pendiente, estado="PENDIENTE")
        for accion in ("pago-simulado", "cerrar"):
            assert client.post(f"/servicios/{pendiente}/{accion}", json={}, headers=headers).status_code == 409
        assert client.post(f"{ruta}/cerrar", json={}, headers=headers).status_code == 409

    assert client.post(f"{ruta}/pago-simulado", json={}, headers=headers).status_code == 201
    assert client.get(ruta).json["data"]["pago"]["importe"] == "5000.00"
    assert client.post(f"{ruta}/pago-simulado", json={}, headers=headers).status_code == 409
    assert client.post(f"{ruta}/cerrar", json={}, headers=headers).status_code == 200
    assert all(item["id"] != servicio_id for item in client.get(listado).json["data"])
    with app.app_context():
        pago = db.session.execute(db.select(Pago).filter_by(servicio_id=servicio_id)).scalar_one()
        assert pago.importe == Decimal("5000.00")
        servicio = db.session.get(Servicio, servicio_id)
        assert servicio.estado == "CERRADO"
        assert db.session.get(Mesa, servicio.mesa_id).estado == "DISPONIBLE"
