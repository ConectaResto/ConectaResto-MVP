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
    '/categories': [{id: 4, name: '<img src=x onerror=alert(1)>', description: 'Descripcion'}],
    '/admin/products': [{id: 5, name: 'Cafe', description: '', price: '12.35', categoria_id: 4, is_available: true}],
    '/users': [{id: 6, username: 'mesero', email: 'a@example.test', rol: 'WAITER', is_active: true}],
};
const calls = []; let failure = null; let meRole = 'ADMIN';
global.fetch = async (url, options = {}) => {
    calls.push({url, ...options});
    const error = failure; failure = null;
    if (!error && url === '/products/5' && options.method === 'PATCH') {
        Object.assign(records['/admin/products'][0], JSON.parse(options.body));
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
    assert.deepEqual(calls.map(call => call.url), ['/auth/me', '/admin/mesas', '/categories', '/admin/products', '/users']);
    assert.equal(sections[1].nodes['[data-rows]'].children[0].children[1].textContent, records['/categories'][0].name);
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
        assert.equal(calls.at(-1).url, '/admin/products');
        assert.equal(products.nodes['[data-rows]'].children[0].children[4].textContent, label);
    }
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
