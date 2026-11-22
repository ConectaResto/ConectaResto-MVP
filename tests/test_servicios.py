import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from decimal import Decimal

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.catalog.models import Category, Product
from app.mesas.models import Mesa
from app.pedidos.models import DetallePedido, Pedido
from app.pedidos.service import PedidoError, crear_pedido
from app.servicios.models import Pago, Servicio
from app.servicios.service import abrir_servicio
from app.users.models import Rol, Usuario


def autenticar(client, role="WAITER", nombre="operador"):
    rol = db.session.execute(db.select(Rol).where(Rol.name == role)).scalar_one_or_none()
    if rol is None:
        rol = Rol(name=role)
    usuario = Usuario(username=nombre, email=f"{nombre}@example.test", rol=rol)
    usuario.set_password("test-password")
    db.session.add(usuario)
    db.session.commit()
    csrf = client.get("/auth/csrf").json["data"]["csrf_token"]
    assert client.post("/auth/login", json={
        "username": nombre, "password": "test-password",
    }, headers={"X-CSRF-Token": csrf}).status_code == 200
    token = client.get("/auth/csrf").json["data"]["csrf_token"]
    return usuario, {"X-CSRF-Token": token}


@pytest.fixture
def mesa(app):
    mesa = Mesa(numero=1)
    db.session.add(mesa)
    db.session.commit()
    return mesa


def test_abrir_consultar_y_no_duplicar(client, mesa):
    usuario, headers = autenticar(client)
    response = client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers)
    assert response.status_code == 201
    servicio = response.json["data"]
    assert servicio == {"id": servicio["id"], "mesa_id": mesa.id,
                        "mesa_numero": mesa.numero,
                        "abierto_por_id": usuario.id, "estado": "ACTIVO", "pedidos": [],
                        "total": "0.00", "pago": None}
    db.session.refresh(mesa)
    assert mesa.estado == "OCUPADA"
    assert client.get(f'/servicios/{servicio["id"]}').json["data"] == servicio
    assert client.get("/servicios?estado=ACTIVO").json["data"] == [servicio]
    assert client.get("/servicios?estado=CERRADO").json["data"] == []
    assert client.get("/servicios?estado=INVALIDO").status_code == 400
    assert client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers).status_code == 409
    assert Servicio.query.count() == 1


@pytest.mark.parametrize("estado", ["OCUPADA", "CERRADA"])
def test_mesa_no_disponible(client, mesa, estado):
    _, headers = autenticar(client)
    mesa.estado = estado
    db.session.commit()
    assert client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers).status_code == 409
    assert Servicio.query.count() == 0
    assert mesa.estado == estado


def test_servicio_preexistente_impide_apertura_y_revierte_mesa(client, mesa):
    usuario, headers = autenticar(client)
    db.session.add(Servicio(mesa_id=mesa.id, abierto_por_id=usuario.id, estado="ACTIVO"))
    db.session.commit()
    assert client.post("/servicios", json={"mesa_id": mesa.id}, headers=headers).status_code == 409
    db.session.refresh(mesa)
    assert mesa.estado == "DISPONIBLE"
    assert Servicio.query.count() == 1


@pytest.mark.parametrize("data", [None, [], {}, {"mesa_id": True}, {"mesa_id": 0},
    {"mesa_id": -1}, {"mesa_id": "1"}, {"mesa_id": 1.5}, {"mesa_id": 2147483648},
    {"mesa_id": 1, "estado": "ACTIVO"}])
def test_validacion_apertura(client, mesa, data):
    _, headers = autenticar(client)
    assert client.post("/servicios", json=data, headers=headers).status_code == 400
    assert Servicio.query.count() == 0
    assert mesa.estado == "DISPONIBLE"


def test_recursos_inexistentes(client):
    _, headers = autenticar(client)
    assert client.get("/servicios/999").status_code == 404
    assert client.post("/servicios", json={"mesa_id": 999}, headers=headers).status_code == 404


@pytest.mark.parametrize("servicio_id", [
    "0", "-1", "abc", "1.5", "2147483648", "9223372036854775807",
    "9223372036854775808", str(10 ** 100),
])
def test_consulta_servicio_id_invalido_devuelve_404(client, servicio_id, monkeypatch):
    autenticar(client)

    def consultar_no_permitido(*args, **kwargs):
        pytest.fail("Un ID invalido no debe llegar a la consulta de base de datos")

    monkeypatch.setattr(db, "get_or_404", consultar_no_permitido)
    response = client.get(f"/servicios/{servicio_id}")
    assert response.status_code == 404
    assert response.json["success"] is False


@pytest.mark.parametrize("rol", [None, "ADMIN", "KITCHEN", "CASHIER"])
def test_permisos_servicios(client, mesa, rol):
    if rol:
        _, headers = autenticar(client, rol)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    expected = 403 if rol else 401
    for method, path, data in [
        ("GET", "/servicios", None), ("GET", "/servicios/1", None),
        ("POST", "/servicios", {"mesa_id": mesa.id}),
        ("POST", "/servicios/1/pedidos", {"items": []}),
    ]:
        codigo = expected
        if rol == "CASHIER" and method == "GET":
            codigo = 200 if path == "/servicios" else 404
        assert client.open(path, method=method, json=data, headers=headers).status_code == codigo
    assert Servicio.query.count() == 0


def test_csrf_apertura(client, mesa):
    autenticar(client)
    assert client.post("/servicios", json={"mesa_id": mesa.id}).status_code == 400
    assert mesa.estado == "DISPONIBLE"


def test_apertura_revierte_fallo_de_commit(client, mesa, monkeypatch):
    usuario, _ = autenticar(client)
    def fallar():
        db.session.flush()
        raise RuntimeError("fallo de persistencia")
    with monkeypatch.context() as patch:
        patch.setattr(db.session, "commit", fallar)
        with pytest.raises(RuntimeError):
            abrir_servicio(mesa.id, actor=usuario)
    db.session.refresh(mesa)
    assert mesa.estado == "DISPONIBLE"
    assert Servicio.query.count() == 0


def test_aperturas_concurrentes_crean_un_solo_servicio(tmp_path, monkeypatch):
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path / 'aperturas.db'}")
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        usuario = Usuario(username="mesero", email="mesero@example.test", rol=Rol(name="WAITER"))
        usuario.set_password("test-password")
        mesa = Mesa(numero=1)
        db.session.add_all([usuario, mesa])
        db.session.commit()
        usuario_id, mesa_id = usuario.id, mesa.id
    barrera = Barrier(2)

    def abrir():
        with app.app_context():
            actor = db.session.get(Usuario, usuario_id)
            barrera.wait(timeout=10)
            try:
                abrir_servicio(mesa_id, actor=actor)
                return 201
            except PedidoError as error:
                return error.status_code

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(lambda _: abrir(), range(2)))
        assert sorted(resultados) == [201, 409]
        with app.app_context():
            assert Servicio.query.count() == 1
            assert db.session.get(Mesa, mesa_id).estado == "OCUPADA"
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()


def test_listar_servicios_cashier_ver_datos_reales(client, mesa):
    _, wheaders = autenticar(client, "WAITER", "mesero")
    creado = client.post("/servicios", json={"mesa_id": mesa.id}, headers=wheaders)
    assert creado.status_code == 201
    servicio_id = creado.json["data"]["id"]

    _, cheaders = autenticar(client, "CASHIER", "cajero")
    response = client.get("/servicios", headers=cheaders)
    assert response.status_code == 200
    data = response.json["data"]
    assert len(data) == 1
    servicio = data[0]
    assert servicio["id"] == servicio_id
    assert servicio["mesa_id"] == mesa.id
    assert servicio["mesa_numero"] == mesa.numero
    assert servicio["estado"] == "ACTIVO"
    assert servicio["pedidos"] == []
    assert servicio["total"] == "0.00"
    assert servicio["pago"] is None


def test_consultar_servicio_cashier_ver_datos_reales(client, mesa):
    _, wheaders = autenticar(client, "WAITER", "mesero")
    creado = client.post("/servicios", json={"mesa_id": mesa.id}, headers=wheaders)
    servicio_id = creado.json["data"]["id"]

    _, cheaders = autenticar(client, "CASHIER", "cajero")
    response = client.get(f"/servicios/{servicio_id}", headers=cheaders)
    assert response.status_code == 200
    servicio = response.json["data"]
    assert servicio["id"] == servicio_id
    assert servicio["mesa_id"] == mesa.id
    assert servicio["mesa_numero"] == mesa.numero
    assert servicio["estado"] == "ACTIVO"
    assert servicio["total"] == "0.00"
    assert servicio["pago"] is None
    assert "pedidos" in servicio


def _crear_servicio_con_pedido_entregado(client, mesa_id, producto_id, cantidad=1):
    """Crea un servicio y un pedido ENTREGADO para pruebas de caja."""
    mesero, wheaders = autenticar(client, "WAITER", "mesero")
    servicio_id = client.post("/servicios", json={"mesa_id": mesa_id},
                              headers=wheaders).json["data"]["id"]
    pedido = crear_pedido(servicio_id, [{"producto_id": producto_id, "cantidad": cantidad}],
                          origen="MESERO", creado_por_id=mesero.id)
    pedido.estado = "ENTREGADO"
    pedido.estado_preparacion = "LISTO_PARA_SERVIR"
    db.session.commit()
    _, cheaders = autenticar(client, "CASHIER", "cajero")
    return servicio_id, cheaders


def test_cashier_pago_simulado_con_mesa_numero(client, mesa):
    categoria = Category(name="Bebidas")
    db.session.add(categoria)
    db.session.flush()
    producto = Product(name="Cafe", price=Decimal("10.00"), categoria_id=categoria.id)
    db.session.add(producto)
    db.session.commit()
    servicio_id, cheaders = _crear_servicio_con_pedido_entregado(client, mesa.id, producto.id)
    response = client.post(f"/servicios/{servicio_id}/pago-simulado",
                           headers=cheaders)
    assert response.status_code == 201
    servicio = response.json["data"]
    assert servicio["mesa_id"] == mesa.id
    assert servicio["mesa_numero"] == mesa.numero
    assert servicio["estado"] == "ACTIVO"
    assert servicio["pago"] is not None


def test_cashier_cerrar_con_mesa_numero(client, mesa):
    categoria = Category(name="Bebidas")
    db.session.add(categoria)
    db.session.flush()
    producto = Product(name="Cafe", price=Decimal("10.00"), categoria_id=categoria.id)
    db.session.add(producto)
    db.session.commit()
    servicio_id, cheaders = _crear_servicio_con_pedido_entregado(client, mesa.id, producto.id)
    client.post(f"/servicios/{servicio_id}/pago-simulado", headers=cheaders)
    response = client.post(f"/servicios/{servicio_id}/cerrar", headers=cheaders)
    assert response.status_code == 200
    servicio = response.json["data"]
    assert servicio["mesa_id"] == mesa.id
    assert servicio["mesa_numero"] == mesa.numero
    assert servicio["estado"] == "CERRADO"


def test_mesa_id_diferente_de_numero(client):
    """Verifica mesa_id (PK interna) y mesa_numero (numero visible) son distintos cuando corresponden."""
    _, wheaders = autenticar(client, "WAITER", "mesero")
    mesa_visible = Mesa(numero=12)
    db.session.add(mesa_visible)
    db.session.commit()
    assert mesa_visible.id != mesa_visible.numero
    creado = client.post("/servicios", json={"mesa_id": mesa_visible.id},
                         headers=wheaders)
    assert creado.status_code == 201
    servicio = creado.json["data"]
    assert servicio["mesa_id"] == mesa_visible.id
    assert servicio["mesa_numero"] == mesa_visible.numero
    assert servicio["mesa_id"] != servicio["mesa_numero"]


def test_cashier_no_acceso_mesas(client):
    """CASHIER no puede consultar GET /mesas (protección de permisos existente)."""
    _, cheaders = autenticar(client, "CASHIER", "cajero")
    response = client.get("/mesas", headers=cheaders)
    assert response.status_code == 403
