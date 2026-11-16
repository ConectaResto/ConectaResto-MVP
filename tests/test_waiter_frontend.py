import pytest

from app.extensions import db
from app.models import Rol, Usuario


@pytest.fixture
def waiter_role(app):
    with app.app_context():
        rol = Rol(name="WAITER", description="Mesero de sala")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def admin_role(app):
    with app.app_context():
        rol = Rol(name="ADMIN", description="Administrador del sistema")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def kitchen_role(app):
    with app.app_context():
        rol = Rol(name="KITCHEN", description="Personal de cocina")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def cashier_role(app):
    with app.app_context():
        rol = Rol(name="CASHIER", description="Cajero de punto de venta")
        db.session.add(rol)
        db.session.commit()
        return rol


@pytest.fixture
def waiter_user(app, waiter_role):
    with app.app_context():
        user = Usuario(username="mesero1", email="mesero1@test.com", rol=waiter_role)
        user.set_password("waiter-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def admin_user(app, admin_role):
    with app.app_context():
        user = Usuario(username="admin1", email="admin1@test.com", rol=admin_role)
        user.set_password("admin-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def kitchen_user(app, kitchen_role):
    with app.app_context():
        user = Usuario(username="cocina1", email="cocina1@test.com", rol=kitchen_role)
        user.set_password("kitchen-pass")
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def cashier_user(app, cashier_role):
    with app.app_context():
        user = Usuario(username="caja1", email="caja1@test.com", rol=cashier_role)
        user.set_password("cashier-pass")
        db.session.add(user)
        db.session.commit()
        return user


def csrf_token(client):
    return client.get("/auth/csrf").json["data"]["csrf_token"]


def login(client, username, password):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": csrf_token(client)},
    )


# ---------- Waiter: Mesas ----------
def test_waiter_can_access_mesas(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mesas" in html
    assert "Panel Mesero" in html


def test_waiter_mesas_requires_auth(client):
    response = client.get("/waiter/mesas", follow_redirects=False)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html
    assert "Panel Mesero" not in html


# ---------- Waiter: Pedidos ----------
def test_waiter_can_access_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Mesero" in html


def test_waiter_pedidos_requires_auth(client):
    response = client.get("/waiter/pedidos", follow_redirects=False)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html
    assert "Panel Mesero" not in html


# ---------- Waiter: Role isolation ----------
def test_admin_cannot_access_waiter_mesas(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_waiter_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_waiter_mesas(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_waiter_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_waiter_mesas(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_waiter_pedidos(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 403

def test_carrito_renderiza_texto_y_conserva_agregar_quitar_totales():
    from pathlib import Path
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node opcional para verificar JavaScript vanilla")
    source = Path(__file__).resolve().parents[1] / "app/templates/waiter/pedidos.html"
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.style = {}; this.events = {}; }
    replaceChildren() { this.children = []; }
    appendChild(child) { this.children.push(child); }
    addEventListener(name, fn) { this.events[name] = fn; }
    set innerHTML(value) { throw Error('Insercion HTML insegura'); }
}
global.document = {createElement: tag => new Element(tag)};
global.window = {};
global.itemsList = new Element('div');
global.addItemBtn = new Element('button');
global.productoSelect = {value: '1', selectedIndex: 0, options: [{text: '<img src=x onerror=alert(1)> - $5.25'}]};
global.cantidadInput = {value: '2'};
global.flashEl = {style: {}};
global.showFlash = () => {};
const source = fs.readFileSync(process.argv[2], 'utf8');
vm.runInThisContext('let items = [];\n' + source.slice(source.indexOf('    function renderItems()'), source.indexOf('    async function loadPedidos()')));
renderItems();
assert.equal(itemsList.children[0].textContent, 'Sin productos agregados.');
addItemBtn.events.click();
assert.equal(itemsList.children[0].children[0].textContent, '<img src=x onerror=alert(1)> x2');
assert.equal(itemsList.children[0].children[0].children.length, 1);
assert.equal(itemsList.children[1].textContent, 'Total: $10.50');
productoSelect.options[0].text = 'Agua - $3.10'; cantidadInput.value = '1';
addItemBtn.events.click();
assert.equal(itemsList.children[1].textContent, 'Total: $13.60');
itemsList.children[0].children[0].children[0].events.click();
assert.equal(itemsList.children[0].children[0].textContent, 'Agua x1');
assert.equal(itemsList.children[1].textContent, 'Total: $3.10');
itemsList.children[0].children[0].children[0].events.click();
assert.equal(itemsList.children[0].textContent, 'Sin productos agregados.');
cantidadInput.value = '0'; addItemBtn.events.click();
assert.equal(itemsList.children[0].textContent, 'Sin productos agregados.');
"""
    result = subprocess.run([node, "-", str(source)], input=harness, text=True,
                            encoding="utf-8", capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("relative_path", [
    "app/static/js/admin.js",
    "app/static/js/cashier.js",
    "app/templates/waiter/mesas.html",
    "app/templates/waiter/pedidos.html",
    "app/templates/kitchen/pedidos.html",
])
def test_etiquetas_estados_legibles(relative_path):
    from pathlib import Path
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node opcional para verificar JavaScript vanilla")
    source = Path(__file__).resolve().parents[1] / relative_path
    harness = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
const script = source.includes('<script>') ? source.split('<script>')[1].split('</script>')[0] : source;
new vm.Script(script);
const start = source.indexOf('    function estadoLegible(');
const end = source.indexOf('\n    }', start) + 6;
vm.runInThisContext(source.slice(start, end));
const expected = {
 DISPONIBLE:'Disponible', OCUPADA:'Ocupada', CERRADA:'Cerrada', ACTIVO:'Activo', CERRADO:'Cerrado',
 PENDIENTE:'Pendiente', EN_PREPARACION:'En preparaci\u00f3n', LISTO:'Listo', ENTREGADO:'Entregado',
 NO_ENVIADO:'No enviado', RECIBIDO:'Recibido', EN_COCINA:'En cocina', LISTO_PARA_SERVIR:'Listo para servir'
};
for (const [state,label] of Object.entries(expected)) assert.equal(estadoLegible(state),label);
for (const state of [null,undefined,'__proto__','<img src=x onerror=alert(1)>','OTRO_ESTADO']) {
 assert.equal(estadoLegible(state),'Estado desconocido');
}
"""
    result = subprocess.run([node, "-", str(source)], input=harness, text=True,
                            encoding="utf-8", capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
