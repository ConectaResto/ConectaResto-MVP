from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess

import pytest

from tests.test_servicios import autenticar


class PanelHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.mark.parametrize("path", ["/admin", "/panel/admin"])
def test_admin_renderiza_gestiones_y_script_propio(app, client, path):
    autenticar(client, "ADMIN")
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parsed = PanelHTML(html)
    sections = {attrs["data-admin-section"] for _, attrs in parsed.elements if "data-admin-section" in attrs}
    assert sections == {"mesas", "categorias", "productos", "usuarios"}
    assert {attrs["id"] for tag, attrs in parsed.elements if tag == "form"} == {
        "form-mesas", "form-categorias", "form-productos", "form-usuarios",
    }
    assert any(tag == "script" and attrs.get("src") == "/static/js/admin.js" for tag, attrs in parsed.elements)
    assert any(tag == "meta" and attrs.get("name") == "csrf-token" and attrs.get("content") for tag, attrs in parsed.elements)
    password = next(attrs for tag, attrs in parsed.elements if tag == "input" and attrs.get("name") == "password")
    assert password["type"] == "password"
    assert password["autocomplete"] == "new-password"
    assert "value" not in password
    assert "test-password" not in html
    assert "password_hash" not in html
    assert 'href="#admin-mesas"' in html
    assert "Los productos no disponibles siguen en esta lista" in html
    role_labels = {"WAITER": "Mesero", "KITCHEN": "Cocina", "CASHIER": "Cajero", "ADMIN": "Administrador"}
    for value, label in role_labels.items():
        assert f'<option value="{value}">{label}</option>' in html
    assert {attrs.get("value") for tag, attrs in parsed.elements
            if tag == "option" and attrs.get("value") in role_labels} == set(role_labels)


def test_admin_puede_reactivar_un_producto_sin_publicarlo_mientras_no_esta_disponible(app, client):
    _, headers = autenticar(client, "ADMIN")
    publico = app.test_client()
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers)
    assert category.status_code == 201
    payload = {"name": "Café", "price": "12.35", "categoria_id": category.json["data"]["id"]}
    response = client.post("/products", json=payload, headers=headers)
    assert response.status_code == 201
    product_id = response.json["data"]["id"]
    path = f"/products/{product_id}"

    for available in (True, False, True):
        response = client.patch(path, json={"is_available": available}, headers=headers)
        assert response.status_code == 200
        admin_products = client.get("/admin/products")
        assert admin_products.status_code == 200
        [product] = admin_products.json["data"]
        assert product["id"] == product_id
        assert product["is_available"] is available
        public_ids = [row["id"] for row in publico.get("/products").json["data"]]
        assert public_ids == ([product_id] if available else [])
        assert publico.get(path).status_code == (200 if available else 404)

    assert client.delete(path, headers=headers).status_code == 200
    assert client.get("/admin/products").json["data"] == []


@pytest.mark.parametrize("role, status", [(None, 401), ("WAITER", 403), ("KITCHEN", 403), ("CASHIER", 403)])
def test_catalogo_administrativo_y_disponibilidad_requieren_admin(client, role, status):
    if role:
        _, headers = autenticar(client, role)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    assert client.get("/admin/products").status_code == status
    assert client.patch("/products/1", json={"is_available": False}, headers=headers).status_code == status
    assert client.get("/products").status_code == 200


@pytest.mark.parametrize("path", ["/admin", "/panel/admin"])
@pytest.mark.parametrize("role", ["WAITER", "KITCHEN", "CASHIER"])
def test_otros_roles_no_acceden_admin(client, role, path):
    autenticar(client, role)
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 403
    assert 'id="admin-panel"' not in response.get_data(as_text=True)
    assert 'src="/static/js/admin.js"' not in response.get_data(as_text=True)


@pytest.mark.parametrize("path", ["/admin", "/panel/admin"])
def test_admin_sin_sesion_muestra_login_sin_formularios(client, path):
    response = client.get(path, follow_redirects=True)
    html = response.get_data(as_text=True)
    assert 'id="login-form"' in html
    assert 'id="admin-panel"' not in html


def test_script_admin_se_sirve_y_no_se_carga_en_otros_paneles(client):
    response = client.get("/static/js/admin.js")
    assert response.status_code == 200
    assert "DOMContentLoaded" in response.get_data(as_text=True)
    for role in ("WAITER", "KITCHEN", "CASHIER"):
        autenticar(client, role, "usuario_" + role)
        response = client.get("/panel/" + role.lower())
        assert response.status_code == 200
        assert '/static/js/admin.js' not in response.get_data(as_text=True)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node opcional para verificar JavaScript vanilla")
def test_javascript_formularios_csrf_errores_y_qr():
    """Ejecuta los handlers reales con DOM y transporte simulados, sin paquetes JS."""
    source = Path(__file__).resolve().parents[1] / "app/static/js/admin.js"
    harness = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
class Element {
    constructor() { this.dataset = {}; this.children = []; this.events = {}; this.value = ''; this.type = 'text'; this.hidden = false; }
    addEventListener(event, handler) { this.events[event] = handler; }
    appendChild(child) { this.children.push(child); }
    replaceChildren(...children) { this.children = children; }
    setAttribute(key, value) { this[key] = value; }
    removeAttribute(key) { delete this[key]; }
    focus() {}
    add(option) { this.children.push(option); }
    set innerHTML(value) { throw Error('Datos insertados mediante innerHTML'); }
}
const fields = {
    mesas: ['numero', 'estado'], categorias: ['name', 'description'],
    productos: ['name', 'description', 'price', 'categoria_id', 'is_available'],
    usuarios: ['username', 'email', 'rol', 'password'],
};
const sections = Object.entries(fields).map(([name, names]) => {
    const section = new Element(); section.dataset.adminSection = name;
    section.nodes = {};
    for (const selector of ['[data-feedback]', '[data-form-title]', '[data-list-status]', '[data-rows]', '[data-refresh]', '[data-cancel]', 'fieldset']) section.nodes[selector] = new Element();
    const form = new Element(); form.elements = { namedItem: key => form.elements[key] };
    names.forEach(key => { form.elements[key] = new Element(); });
    if (form.elements.is_available) form.elements.is_available.type = 'checkbox';
    form.reset = () => { names.forEach(key => { form.elements[key].value = ''; form.elements[key].checked = key === 'is_available'; }); };
    form.reportValidity = () => true;
    form.querySelector = () => form.elements[names[0]];
    section.nodes.form = form;
    section.querySelector = selector => section.nodes[selector];
    section.querySelectorAll = () => [section.nodes['[data-refresh]'], section.nodes['[data-cancel]']];
    return section;
});
const ids = Object.fromEntries(sections.map(section => ['admin-' + section.dataset.adminSection, section]));
for (const id of ['mesa-qr', 'mesa-qr-image', 'mesa-qr-title', 'cerrar-qr']) ids[id] = new Element();
ids['producto-categoria'] = sections[2].nodes.form.elements.categoria_id;
const panel = new Element(); panel.querySelectorAll = () => sections; ids['admin-panel'] = panel;
let ready;
global.document = {
    getElementById: id => ids[id],
    querySelector: () => ({content: 'csrf-test'}),
    createElement: () => new Element(),
    addEventListener: (event, callback) => { ready = callback; },
};
global.Option = function(text, value) { const item = new Element(); item.textContent = text; item.value = value; return item; };
let confirmed = true; let redirected;
global.window = { confirm: () => confirmed, addEventListener() {}, location: { assign: path => { redirected = path; } } };
let revoked = false;
global.URL = { createObjectURL: () => 'blob:qr-test', revokeObjectURL: () => { revoked = true; } };
const records = {
    '/admin/mesas': [{id: 3, numero: 12, estado: 'DISPONIBLE'}],
    '/categories?include_inactive=true': [{is_active: true, id: 4, name: '<img src=x onerror=alert(1)>', description: 'Descripcion'}, {id: 7, name: 'Inactiva', is_active: false}],
    '/admin/products?include_inactive=true': [{is_active: true, id: 5, name: 'Cafe', description: '', price: '12.35', categoria_id: 4, is_available: true}],
    '/users': [{id: 6, username: 'mesero', email: 'a@example.test', rol: 'WAITER', is_active: true}],
};
const calls = []; let failure = null; let meRole = 'ADMIN';
global.fetch = async (url, options = {}) => {
    calls.push({url, ...options});
    const error = failure; failure = null;
    if (!error && url === '/products/5' && options.method === 'PATCH') {
        Object.assign(records['/admin/products?include_inactive=true'][0], JSON.parse(options.body));
    }
    if (!error && url === '/products/5' && options.method === 'DELETE') {
        records['/admin/products?include_inactive=true'][0].is_active = false;
    }
    const svg = url.endsWith('/qr.svg');
    const data = url === '/auth/me' ? {id: 1, rol: meRole} : url === '/users' ? {users: records[url]} : records[url] || {};
    return { ok: !error, status: error?.status || 200,
        json: async () => error ? {success: false, error: error.message} : {success: true, data},
        headers: {get: () => svg ? 'image/svg+xml' : 'application/json'}, blob: async () => ({}) };
};
vm.runInThisContext(fs.readFileSync(process.argv[2], 'utf8'));
const click = (section, action, id) => section.nodes['[data-rows]'].events.click({target: {closest: () => ({dataset: {action, recordId: String(id)}})}});
const submit = section => section.nodes.form.events.submit({preventDefault() {}});
(async () => {
    await ready();
    assert.deepEqual(calls.map(call => call.url), ['/auth/me', '/admin/mesas', '/categories?include_inactive=true', '/admin/products?include_inactive=true', '/users']);
    assert.equal(sections[1].nodes['[data-rows]'].children[0].children[1].textContent, records['/categories?include_inactive=true'][0].name);
    assert.equal(sections[3].nodes['[data-rows]'].children[0].children[3].textContent, 'Mesero');
    assert.equal(ids['producto-categoria'].children.length, 2);
    assert(!ids['producto-categoria'].children.some(option => option.value === '7'));
    for (const [index, name] of ['mesas', 'categorias', 'productos', 'usuarios'].entries()) {
        const section = sections[index]; const form = section.nodes.form;
        const values = {numero: '12', estado: 'DISPONIBLE', name: 'Nombre', description: 'Descripcion', price: '12.35', categoria_id: '4', username: 'nuevo', email: 'nuevo@example.test', rol: 'WAITER', password: 'synthetic-password'};
        for (const key of fields[name]) { form.elements[key].value = values[key]; form.elements[key].checked = true; }
        await submit(section);
        const call = calls.findLast(call => call.method === 'POST');
        assert.equal(call.url, ['/admin/mesas', '/categories', '/products', '/users'][index]);
        assert.equal(call.headers['X-CSRF-Token'], 'csrf-test');
        assert.equal(call.credentials, 'same-origin');
        if (name === 'productos') assert.equal(JSON.parse(call.body).price, '12.35');
        if (name === 'usuarios') assert.equal(JSON.parse(call.body).rol, 'WAITER');
        if (name === 'usuarios') assert.equal(form.elements.password.value, '');
        const record = Object.values(records)[index][0];
        await click(section, 'editar', record.id);
        if (name === 'usuarios') assert.equal(form.elements.password.required, false);
        await submit(section);
        const patch = calls.findLast(call => call.method === 'PATCH');
        assert.equal(patch.url, call.url + '/' + record.id);
        if (name === 'usuarios') assert.equal('password' in JSON.parse(patch.body), false);
    }
    const products = sections[2];
    const availability = products.nodes.form.elements.is_available;
    for (const [available, label] of [[false, 'No disponible'], [true, 'Disponible']]) {
        await click(products, 'editar', 5);
        assert.equal(availability.checked, !available);
        availability.checked = available;
        await submit(products);
        assert.equal(calls.at(-1).url, '/admin/products?include_inactive=true');
        assert.equal(products.nodes['[data-rows]'].children[0].children[4].textContent, label);
    }
    const productRecord = records['/admin/products?include_inactive=true'][0];
    const productActions = () => products.nodes['[data-rows]'].children[0].children.at(-1).children.map(button => button.dataset.action);
    assert(productActions().includes('desactivar'));
    assert(!productActions().includes('reactivar'));
    assert.match(sections[1].nodes['[data-list-status]'].textContent, /desactiva o reasigna sus productos activos/);
    confirmed = false;
    const beforeCancel = calls.length;
    await click(products, 'desactivar', 5);
    assert.equal(calls.length, beforeCancel);
    assert.equal(productRecord.is_active, true);
    confirmed = true;
    failure = {status: 500, message: 'No se pudo desactivar el producto'};
    await click(products, 'desactivar', 5);
    assert.equal(products.nodes['[data-feedback]'].textContent, 'No se pudo desactivar el producto');
    assert.equal(products.nodes['[data-feedback]'].role, 'alert');
    assert.equal(products.dataset.busy, 'false');
    assert.equal(productRecord.is_active, true);
    // No disponible sigue activo y conserva la opcion Desactivar.
    await click(products, 'editar', 5);
    availability.checked = false;
    await submit(products);
    assert.equal(productRecord.is_active, true);
    assert(productActions().includes('desactivar'));
    await click(products, 'desactivar', 5);
    const deletion = calls.findLast(call => call.method === 'DELETE');
    assert.equal(deletion.url, '/products/5');
    assert.equal(deletion.headers['X-CSRF-Token'], 'csrf-test');
    assert.equal(deletion.credentials, 'same-origin');
    assert.equal(calls.at(-1).url, '/admin/products?include_inactive=true');
    assert.equal(productRecord.is_active, false);
    assert.equal(productRecord.is_available, false);
    assert(productActions().includes('reactivar'));
    assert(!productActions().includes('desactivar'));
    await click(products, 'reactivar', 5);
    assert.equal(productRecord.is_active, true);
    assert.equal(productRecord.is_available, false);
    assert(productActions().includes('desactivar'));
    assert(!productActions().includes('reactivar'));
    for (const [index, path, id] of [[1, '/categories', 4], [2, '/products', 5], [3, '/users', 6]]) {
        Object.values(records)[index][0].is_active = false;
        await sections[index].nodes['[data-refresh]'].events.click();
        const actions = sections[index].nodes['[data-rows]'].children[0].children.at(-1).children;
        assert(actions.some(button => button.textContent === 'Reactivar'));
        await click(sections[index], 'reactivar', id);
        const patch = calls.findLast(call => call.method === 'PATCH');
        assert.equal(patch.url, path + '/' + id);
        assert.deepEqual(JSON.parse(patch.body), {is_active: true});
        assert.equal(patch.headers['X-CSRF-Token'], 'csrf-test');
        Object.values(records)[index][0].is_active = true;
    }
    assert.equal(ids['producto-categoria'].children.length, 2);
    confirmed = false; const before = calls.length;
    await click(sections[1], 'desactivar', 4); assert.equal(calls.length, before);
    confirmed = true; failure = {status: 409, message: 'Categoria con productos activos'};
    await click(sections[1], 'desactivar', 4);
    assert.equal(sections[1].nodes['[data-feedback]'].textContent, 'Categoria con productos activos');
    assert.equal(sections[1].nodes['[data-feedback]'].role, 'alert');
    await click(sections[3], 'desactivar', 6);
    assert.equal(calls.findLast(call => call.method === 'DELETE').url, '/users/6');
    failure = {status: 403, message: 'Prohibido'};
    await sections[3].nodes['[data-refresh]'].events.click();
    assert.match(sections[3].nodes['[data-feedback]'].textContent, /permisos/);
    failure = {status: 401, message: 'No autorizado'};
    await sections[0].nodes['[data-refresh]'].events.click();
    assert.match(sections[0].nodes['[data-feedback]'].textContent, /sesión/);
    await click(sections[0], 'qr', 3);
    assert.equal(ids['mesa-qr-image'].src, 'blob:qr-test');
    assert.equal(ids['mesa-qr'].hidden, false);
    ids['cerrar-qr'].events.click(); assert.equal(revoked, true);
    failure = {status: 500, message: 'PUBLIC_BASE_URL no configurada'};
    await click(sections[0], 'qr', 3);
    assert.equal(ids['mesa-qr'].hidden, true);
    assert.match(sections[0].nodes['[data-feedback]'].textContent, /PUBLIC_BASE_URL/);
    records['/users'].push({id: 1, username: 'admin', email: 'admin@example.test', rol: 'ADMIN', is_active: true});
    await sections[3].nodes['[data-refresh]'].events.click();
    const selfActions = sections[3].nodes['[data-rows]'].children[1].children.at(-1).children;
    assert.equal(selfActions.find(button => button.dataset.action === 'desactivar').disabled, true);
    await click(sections[3], 'editar', 1);
    sections[3].nodes.form.elements.rol.value = 'WAITER';
    meRole = 'WAITER';
    await submit(sections[3]);
    assert.equal(redirected, '/');
    console.log('Handlers ADMIN verificados');
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run([shutil.which("node"), "-", str(source)], input=harness,
                            text=True, encoding="utf-8", capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Handlers ADMIN verificados" in result.stdout


@pytest.mark.parametrize("available", [False, True])
def test_reactivacion_catalogo_conserva_disponibilidad(app, client, available):
    _, headers = autenticar(client, "ADMIN")
    public = app.test_client()
    category = client.post("/categories", json={"name": "Bebidas"}, headers=headers).json["data"]
    cid = category["id"]
    product = client.post("/products", json={"name": "Cafe", "price": "5.25", "categoria_id": cid,
                                             "is_available": available}, headers=headers).json["data"]
    pid = product["id"]
    assert client.delete(f"/products/{pid}", headers=headers).status_code == 200
    assert client.delete(f"/categories/{cid}", headers=headers).status_code == 200
    assert public.get("/categories").json["data"] == []
    assert public.get("/products?include_inactive=true").json["data"] == []
    assert client.get("/categories?include_inactive=true").json["data"][0]["is_active"] is False
    assert client.get("/admin/products?include_inactive=true").json["data"][0]["is_active"] is False
    response = client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 404
    assert client.get("/admin/products?include_inactive=true").json["data"][0]["is_active"] is False
    assert client.patch(f"/categories/{cid}", json={"is_active": True}, headers=headers).status_code == 200
    assert len(public.get("/categories").json["data"]) == 1
    assert public.get("/products").json["data"] == []
    response = client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["is_available"] is available
    assert response.json["data"]["is_active"] is True
    assert len(public.get("/products").json["data"]) == int(available)
    assert public.get(f"/products/{pid}").status_code == (200 if available else 404)
    assert client.patch(f"/products/{pid}", json={"is_active": True}, headers=headers).status_code == 200


@pytest.mark.parametrize("role,status", [(None, 401), ("WAITER", 403), ("KITCHEN", 403), ("CASHIER", 403)])
def test_reactivacion_y_listados_inactivos_solo_admin(client, role, status):
    if role:
        _, headers = autenticar(client, role)
    else:
        headers = {"X-CSRF-Token": client.get("/auth/csrf").json["data"]["csrf_token"]}
    for path in ("/users/1", "/categories/1", "/products/1"):
        assert client.patch(path, json={"is_active": True}, headers=headers).status_code == status
    for path in ("/categories?include_inactive=true", "/admin/products?include_inactive=true"):
        assert client.get(path).status_code == status
    assert client.get("/categories").status_code == 200


@pytest.mark.parametrize("bad", [False, None, 0, 1, "true", "false", [], {}])
def test_reactivacion_rechaza_datos_y_no_aplica_cambios(app, client, bad):
    _, headers = autenticar(client, "ADMIN")
    uid = client.post("/users", json={"username": "cocinero1", "email": "c@example.test",
                                    "rol": "ADMIN", "password": "synthetic"}, headers=headers).json["data"]["id"]
    cid = client.post("/categories", json={"name": "Bebidas"}, headers=headers).json["data"]["id"]
    pid = client.post("/products", json={"name": "Cafe", "price": "5", "categoria_id": cid}, headers=headers).json["data"]["id"]
    for path, field, value in ((f"/users/{uid}", "username", "cocinero1"),
                               (f"/categories/{cid}", "name", "Bebidas"),
                               (f"/products/{pid}", "name", "Cafe")):
        assert client.patch(path, json={field: "Changed", "is_active": bad}, headers=headers).status_code == 400
        assert client.get(path).json["data"][field] == value
        assert client.patch(path, json={"is_active": True}).status_code == 400
    for path in ("/categories?include_inactive=invalid", "/admin/products?include_inactive=invalid"):
        assert client.get(path).status_code == 400


def test_reactivacion_usuario_preserva_password_y_rol(app, client):
    from app.extensions import db
    from app.models import Rol, Usuario
    _, headers = autenticar(client, "ADMIN")
    role = Rol(name="KITCHEN")
    user = Usuario(username="cocinero1", email="c@example.test", rol=role, is_active=False)
    user.set_password("synthetic-password")
    db.session.add(user)
    db.session.commit()
    uid, password_hash = user.id, user.password_hash
    response = client.patch(f"/users/{uid}", json={"is_active": True, "rol": "INVALID"}, headers=headers)
    assert response.status_code == 404
    db.session.refresh(user)
    assert user.is_active is False
    response = client.patch(f"/users/{uid}", json={"is_active": True}, headers=headers)
    assert response.status_code == 200
    assert response.json["data"]["rol"] == "KITCHEN"
    assert "password_hash" not in response.json["data"]
    db.session.refresh(user)
    assert user.password_hash == password_hash
    assert client.patch(f"/users/{uid}", json={"is_active": True}, headers=headers).status_code == 200
    kitchen = app.test_client()
    csrf = kitchen.get("/auth/csrf").json["data"]["csrf_token"]
    assert kitchen.post("/auth/login", json={"username": "cocinero1", "password": "synthetic-password"},
                        headers={"X-CSRF-Token": csrf}).status_code == 200


@pytest.mark.parametrize("payload", [None, [], "true", 1])
def test_patch_catalogo_rechaza_cuerpos_no_objeto(client, payload):
    _, headers = autenticar(client, "ADMIN")
    for path in ("/categories/1", "/products/1"):
        assert client.patch(path, json=payload, headers=headers).status_code == 400


# ---------- Pruebas de navegación por pestañas en ADMIN ----------

def test_admin_muestra_una_seccion_visible_inicialmente(app, client):
    autenticar(client, "ADMIN")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parsed = PanelHTML(html)
    visible = [attrs for _, attrs in parsed.elements
               if attrs.get("class") == "admin-section visible"]
    assert len(visible) == 1
    assert visible[0].get("id") == "admin-mesas"
    hidden = [attrs for _, attrs in parsed.elements
              if attrs.get("class") == "admin-section"]
    assert len(hidden) == 3
    hidden_ids = {attrs.get("id") for attrs in hidden}
    assert hidden_ids == {"admin-categorias", "admin-productos", "admin-usuarios"}


def test_admin_tiene_enlaces_navegacion_pestanas(app, client):
    autenticar(client, "ADMIN")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parsed = PanelHTML(html)
    nav_links = [attrs for tag, attrs in parsed.elements
                 if tag == "a" and attrs.get("href") in ("#admin-mesas", "#admin-categorias",
                                                         "#admin-productos", "#admin-usuarios")]
    assert len(nav_links) == 4
    active = [attrs for attrs in nav_links if attrs.get("aria-current") == "page"]
    assert len(active) == 1
    assert active[0].get("href") == "#admin-mesas"


def test_admin_secciones_tienen_aria_labelledby(app, client):
    autenticar(client, "ADMIN")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parsed = PanelHTML(html)
    sections = [attrs for tag, attrs in parsed.elements
                if tag == "section" and attrs.get("id") in ("admin-mesas", "admin-categorias",
                                                            "admin-productos", "admin-usuarios")]
    assert len(sections) == 4
    for attrs in sections:
        assert attrs.get("aria-labelledby") is not None


def test_admin_hash_invalido_muestra_mesas(app, client):
    autenticar(client, "ADMIN")
    response = client.get("/admin#admin-inexistente", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    parsed = PanelHTML(html)
    visible = [attrs for _, attrs in parsed.elements
               if attrs.get("class") == "admin-section visible"]
    assert len(visible) == 1
    assert visible[0].get("id") == "admin-mesas"
