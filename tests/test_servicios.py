import pytest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Mesa, Rol, Servicio, Usuario
from app.pedidos.service import PedidoError
from app.servicios.service import abrir_servicio


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
                        "abierto_por_id": usuario.id, "estado": "ACTIVO", "pedidos": []}
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
        assert client.open(path, method=method, json=data, headers=headers).status_code == expected
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
