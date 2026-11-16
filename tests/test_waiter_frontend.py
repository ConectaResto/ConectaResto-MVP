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


@pytest.mark.parametrize("relation_error", ["none", "services_http", "tables_http", "services_network", "tables_network"])
def test_pedidos_tres_secciones_y_acciones(relation_error):
    from pathlib import Path
    import shutil
    import subprocess
    node = shutil.which("node")
    if not node:
        pytest.skip("Node opcional para verificar JavaScript vanilla")
    source = Path(__file__).resolve().parents[1] / "app/templates/waiter/pedidos.html"
    harness = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[2], 'utf8');
new vm.Script(source.split('<script>')[1].split('</script>')[0]);
const ids = new Map();
class Element {
 constructor() { this.children=[]; this.style={}; this.attrs={}; this.events={}; this.hidden=true; }
 appendChild(c) { this.children.push(c); }
 replaceChildren(...c) { this.children=c; this.html=''; this.lists=[]; this.buttons=[]; }
 set innerHTML(value) {
  this.html=value;
  this.lists=Array.from(value.matchAll(/<ul data-pedido-items>/g),()=>new Element());
  this.buttons=Array.from(value.matchAll(/data-detalles="(\d+)"/g),m=>{
   const b=new Element(); b.attrs['aria-controls']='pedido-detalles-'+m[1]; b.attrs['aria-expanded']='false';
   ids.set(b.attrs['aria-controls'],new Element()); return b;
  });
 }
 get innerHTML() { return this.html||''; }
 querySelectorAll(q) { return q==='[data-pedido-items]'?this.lists:this.buttons; }
 addEventListener(n,f) { this.events[n]=f; }
 getAttribute(n) { return this.attrs[n]; }
 setAttribute(n,v) { this.attrs[n]=v; }
}
const pending=new Element(), active=new Element(), history=new Element(), calls=[];
const make=(id,state,prep,auth)=>({id,servicio_id:1,estado:state,estado_preparacion:prep,autorizado_por_id:auth,total:'10.00',items:[{producto_id:1,cantidad:id},{producto_id:99,cantidad:2}]});
const orders=[make(2,'PENDIENTE','NO_ENVIADO',null),make(9,'ENTREGADO','LISTO_PARA_SERVIR',3),make(3,'PENDIENTE','NO_ENVIADO',3),make(8,'LISTO','LISTO_PARA_SERVIR',3),make(6,'PENDIENTE','NO_ENVIADO',null),make(4,'ENTREGADO','LISTO_PARA_SERVIR',3),make(7,'EN_PREPARACION','EN_COCINA',3)];
const services=[{id:1,mesa_id:101,estado:'CERRADO'},{id:2,mesa_id:202,estado:'ACTIVO'}];
const tables=[{id:101,numero:12,estado:'CERRADA'},{id:202,numero:5,estado:'OCUPADA'}];
orders.find(p=>p.id===7).servicio_id=2;
orders.find(p=>p.id===3).servicio_id=999;
const relationError=process.argv[3];
const context={window:{},document:{createElement:()=>new Element(),getElementById:id=>ids.get(id)},pedidosList:pending,pedidosCursoList:active,historialList:history,nombresProductos:new Map([[1,'Agua <img src=x>']]),flashEl:new Element(),hideFlash(){},showFlash(){},fetchJson:async(url,options)=>{
 calls.push([url,options]);
 if(url==='/servicios' || url==='/mesas') {
  const prefix=url==='/servicios'?'services':'tables';
  if(relationError===prefix+'_network') throw Error('offline');
  return {ok:relationError!==prefix+'_http',data:{data:url==='/servicios'?services:tables}};
 }
 if(options?.method==='POST'){
  const id=Number(url.split('/')[2]),order=orders.find(p=>p.id===id);
  if(url.endsWith('/autorizar')) order.autorizado_por_id=3;
  if(url.endsWith('/entregar')) order.estado='ENTREGADO';
  if(url.endsWith('/enviar-cocina')) { order.estado='EN_PREPARACION';order.estado_preparacion='RECIBIDO'; }
 }
 return {ok:true,data:{data:orders}};
}};
vm.createContext(context);
const labelStart=source.indexOf('    function estadoLegible(');
vm.runInContext(source.slice(labelStart,source.indexOf('\n    }',labelStart)+6),context);
vm.runInContext(source.slice(source.indexOf('    async function loadPedidos()'),source.indexOf("    crearPedidoBtn.addEventListener")),context);
const rowIds=el=>Array.from(el.innerHTML.matchAll(/data-detalles="(\d+)"/g),m=>Number(m[1]));
const partition=()=>{const all=[...rowIds(pending),...rowIds(active),...rowIds(history)];assert.equal(new Set(all).size,orders.length);assert.deepEqual(all.sort((a,b)=>a-b),orders.map(p=>p.id).sort((a,b)=>a-b));};
(async()=>{
 await context.loadPedidos();
 assert.deepEqual(calls.map(([url])=>url),['/pedidos','/servicios','/mesas']);
 for(const section of [pending,active,history]) assert(section.innerHTML.includes('colspan="7"'));
 if(relationError==='none') {
  assert.equal((pending.innerHTML.match(/Mesa 12/g)||[]).length,2);
  assert(history.innerHTML.includes('Mesa 12'));assert(active.innerHTML.includes('Mesa 5'));
  assert(active.innerHTML.includes('Mesa desconocida'));
 } else {
  for(const section of [pending,active,history]) {
   assert(section.innerHTML.includes('Mesa desconocida'));
   assert(!/Mesa (12|5|101|202)/.test(section.innerHTML));
  }
 }
 assert(pending.innerHTML.includes('font-weight:600'));assert(active.innerHTML.includes('font-weight:600'));
 assert(!history.innerHTML.includes('font-weight:600'));
 assert.deepEqual(rowIds(pending),[6,2]);assert.deepEqual(rowIds(active),[8,7,3]);assert.deepEqual(rowIds(history),[9,4]);partition();
 assert(pending.innerHTML.includes('autorizarPedido('));assert(!active.innerHTML.includes('autorizarPedido('));
 assert(active.innerHTML.includes('enviarCocina(3)'));assert(active.innerHTML.includes('entregarPedido(8)'));
 assert(!/autorizarPedido\(|enviarCocina\(|entregarPedido\(/.test(history.innerHTML));
 assert(active.innerHTML.includes('En preparaci\u00f3n'));assert(history.innerHTML.includes('Entregado'));
 for(const section of [pending,active,history]) {
  const id=rowIds(section)[0];assert.equal(section.lists[0].children[0].textContent,id+' \u00d7 Agua <img src=x>');
  assert.equal(section.lists[0].children[1].textContent,'2 \u00d7 Producto #99');
  const button=section.buttons[0], row=ids.get(button.attrs['aria-controls']);const count=calls.length;
  button.events.click();assert.equal(row.hidden,false);assert.equal(button.attrs['aria-expanded'],'true');
  button.events.click();assert.equal(row.hidden,true);assert.equal(calls.length,count);
 }
 await context.window.autorizarPedido(6);await new Promise(setImmediate);assert.deepEqual(rowIds(pending),[2]);assert.deepEqual(rowIds(active),[8,7,6,3]);partition();
 await context.window.enviarCocina(6);await new Promise(setImmediate);assert(active.innerHTML.includes('Recibido'));partition();
 await context.window.entregarPedido(8);await new Promise(setImmediate);assert.deepEqual(rowIds(history),[9,8,4]);assert(!rowIds(active).includes(8));partition();
 await context.loadPedidos();partition();assert.equal(history.lists.length,3);
 assert.deepEqual(calls.filter(([,o])=>o).map(([u,o])=>[u,o.method,o.body]),[['/pedidos/6/autorizar','POST','{}'],['/pedidos/6/enviar-cocina','POST','{}'],['/pedidos/8/entregar','POST','{}']]);
 assert(!calls.some(([u])=>u==='/products'));
 const loads=calls.filter(([u])=>u==='/pedidos').length;
 assert.equal(calls.filter(([u])=>u==='/servicios').length,loads);
 assert.equal(calls.filter(([u])=>u==='/mesas').length,loads);
 orders.length=0;await context.loadPedidos();
 assert.equal(pending.children[0].textContent,'No hay pedidos pendientes de autorizaci\u00f3n.');
 assert.equal(active.children[0].textContent,'No hay pedidos en curso.');
 assert.equal(history.children[0].textContent,'No hay pedidos entregados en el historial.');
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run([node, "-", str(source), relation_error], input=harness, text=True,
                            encoding="utf-8", capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
