import pytest

from app.extensions import db
from app.users.models import Rol, Usuario


@pytest.fixture
def kitchen_role(app):
    with app.app_context():
        rol = Rol(name="KITCHEN", description="Personal de cocina")
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
def waiter_role(app):
    with app.app_context():
        rol = Rol(name="WAITER", description="Mesero de sala")
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
def kitchen_user(app, kitchen_role):
    with app.app_context():
        user = Usuario(username="cocina1", email="cocina1@test.com", rol=kitchen_role)
        user.set_password("kitchen-pass")
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
def waiter_user(app, waiter_role):
    with app.app_context():
        user = Usuario(username="mesero1", email="mesero1@test.com", rol=waiter_role)
        user.set_password("waiter-pass")
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


# ---------- Kitchen: Pedidos ----------
def test_kitchen_can_access_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Cocina" in html


def test_kitchen_pedidos_requires_auth(client):
    response = client.get("/kitchen/pedidos", follow_redirects=False)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html
    assert "Panel Cocina" not in html


# ---------- Kitchen: Role isolation ----------
def test_admin_cannot_access_kitchen_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_kitchen_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_kitchen_pedidos(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403

def test_kitchen_renderiza_activos_historial_y_actualizacion(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    html = client.get("/kitchen/pedidos").get_data(as_text=True)
    assert 'id="pedidos-list"' in html
    assert 'id="pedidos-historial"' in html
    assert 'id="actualizar-pedidos"' in html
    assert '<h2 id="pedidos-activos-title">Pedidos activos</h2>' in html
    assert 'Historial' in html


def test_kitchen_clasificacion_transiciones_y_responsive_en_navegador(
    app, client, kitchen_user, tmp_path,
):
    import os
    import shutil
    import subprocess
    import threading
    import time
    from pathlib import Path

    from werkzeug.serving import make_server
    from app.catalog.models import Category, Product
    from app.mesas.models import Mesa
    from app.pedidos.models import DetallePedido, Pedido
    from app.servicios.models import Servicio
    from tests.browser_helpers import CDP_SETUP
    from tests.test_servicios import autenticar

    node = shutil.which("node")
    browser = next((p for p in (
        os.environ.get("PUBLIC_MENU_TEST_BROWSER", ""),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ) if p and Path(p).is_file()), None)
    if not node or not browser:
        pytest.skip("Requiere Node y Chromium ya instalados")

    waiter, _ = autenticar(client, "WAITER", "mesero_browser")
    category = Category(name="Kitchen browser")
    mesa = Mesa(numero=77, estado="OCUPADA")
    db.session.add_all([category, mesa])
    db.session.flush()
    products = [Product(name=name, price="12.35", categoria_id=category.id,
                        is_available=available) for name, available in (
        ("Cafe <img src=x onerror=alert(1)>", True), ("Sopa", True), ("Retirado", False),
    )]
    db.session.add_all(products)
    service = Servicio(mesa_id=mesa.id, abierto_por_id=waiter.id, estado="ACTIVO")
    db.session.add(service)
    db.session.flush()
    orders = []
    # Deliberately interleave history, active and hidden orders to catch index drift.
    for prep, state, product_index, quantity in (
        ("LISTO_PARA_SERVIR", "ENTREGADO", 1, 3),
        ("RECIBIDO", "EN_PREPARACION", 0, 2),
        ("EN_COCINA", "EN_PREPARACION", 2, 4),
        ("NO_ENVIADO", "PENDIENTE", 0, 1),
    ):
        order = Pedido(servicio_id=service.id, origen="MESERO", estado=state,
                       estado_preparacion=prep,
                       autorizado_por_id=waiter.id if prep != "NO_ENVIADO" else None)
        order.detalles = [DetallePedido(producto_id=products[product_index].id,
                                       cantidad=quantity, precio_unitario="12.35")]
        db.session.add(order)
        orders.append(order)
    db.session.commit()
    ids = [p.id for p in orders]
    fallback_id = products[2].id

    script = CDP_SETUP + r"""
 await send('Page.enable');
 await send('Page.addScriptToEvaluateOnNewDocument',{source:`
  window.auditCalls=[];window.auditFail='';window.auditEmpty=false;
  const realFetch=window.fetch.bind(window);
  window.fetch=(url,opts={})=>{
   if(url==='/pedidos'){
    window.auditCalls.push({url,method:'GET'});
    if(window.auditFail==='load')return Promise.resolve(new Response(JSON.stringify({success:false,error:'Fallo de lectura controlado'}),{status:500}));
    if(window.auditEmpty)return Promise.resolve(new Response(JSON.stringify({success:true,data:[]}),{status:200}));
   }
   if(opts.method==='PATCH'){
    window.auditCalls.push({url,method:'PATCH',body:JSON.parse(opts.body),csrf:!!opts.headers['X-CSRF-Token']});
    if(window.auditFail==='patch')return Promise.resolve(new Response(JSON.stringify({success:false,error:'Transicion rechazada'}),{status:409}));
    if(window.auditFail==='network')return Promise.reject(new Error('Fallo de red controlado'));
   }
   if(url==='/products' && window.auditFail==='catalog')return Promise.reject(new Error('Catalogo sin conexion'));
   return realFetch(url,opts);
  };`});
 const ids=IDS;
 const rows=selector=>run(`Array.from(document.querySelectorAll('${selector} [data-pedido-id]')).map(r=>Number(r.dataset.pedidoId))`);
 const reads=()=>run("auditCalls.filter(c=>c.method==='GET').length");
 const idle=()=>until("document.querySelector('#pedidos-list')?.getAttribute('aria-busy')==='false' && !document.querySelector('#actualizar-pedidos').disabled");
 await send('Page.navigate',{url:base+'/login'});
 await until("document.readyState==='complete' && document.querySelector('#login-form')");
 await run("document.querySelector('[name=username]').value='cocina1';document.querySelector('[name=password]').value='kitchen-pass';document.querySelector('#login-form').requestSubmit()");
 await until("location.pathname==='/panel/kitchen'");
 await send('Page.navigate',{url:base+'/kitchen/pedidos'});await idle();
 assert.deepEqual(await rows('#pedidos-list'),[ids[1],ids[2]]);
 assert.deepEqual(await rows('#pedidos-historial'),[ids[0]]);
 assert.equal(await reads(),1);
 assert.equal(await run("document.querySelector('#pedidos-historial button')===null"),true);
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[1]}"] [data-pedido-items]').textContent`),'2 \u00d7 Cafe <img src=x onerror=alert(1)>');
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[2]}"] [data-pedido-items]').textContent`),'4 \u00d7 Producto #FALLBACK');
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[0]}"] [data-pedido-items]').textContent`),'3 \u00d7 Sopa');
 assert.equal(await run("document.querySelector('[data-pedido-items] img')===null"),true);
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[1]}"] button').textContent`),'En cocina');
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[2]}"] button').textContent`),'Listo para servir');
 for(const width of [1280,768,375]){
  await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:width===375});
  assert.equal(await run('document.documentElement.scrollWidth<=innerWidth'),true);
  await capture(imagePath.replace('desktop',String(width)));
  if(width===375){
   assert.equal(await run("getComputedStyle(document.querySelector('#pedidos-list')).overflowX"),'auto');
   await run("const wrap=document.querySelector('#pedidos-list');wrap.scrollLeft=wrap.scrollWidth;");
   assert.equal(await run("document.querySelector('#pedidos-list button').getBoundingClientRect().right<=innerWidth"),true);
   await capture(imagePath.replace('desktop','375-actions'));
  }
 }
 await click(`[data-pedido-id="${ids[1]}"] button`);await idle();
 assert.equal(await reads(),2);
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[1]}"] button').textContent`),'Listo para servir');
 assert.equal(await run("document.querySelector('#flash-kitchen').style.display"),'block');
 await click(`[data-pedido-id="${ids[1]}"] button`);await idle();
 assert.equal(await reads(),3);
 assert.deepEqual(await rows('#pedidos-list'),[ids[2]]);
 assert.deepEqual(await rows('#pedidos-historial'),[ids[0],ids[1]]);
 assert.match(await text('flash-kitchen'),/listo para servir/);
 assert.equal(await run("document.querySelector('#flash-kitchen').style.display"),'block');
 assert.equal(await run("new Set(Array.from(document.querySelectorAll('[data-pedido-id]')).map(r=>r.dataset.pedidoId)).size"),3);
 const patches=await run("auditCalls.filter(c=>c.method==='PATCH')");
 assert.deepEqual(patches.map(p=>p.body),[{estado:'EN_COCINA'},{estado:'LISTO_PARA_SERVIR'}]);
 assert(patches.every(p=>p.csrf));
 await run("auditFail='patch'");await click(`[data-pedido-id="${ids[2]}"] button`);await idle();
 assert.equal(await text('flash-kitchen'),'Transicion rechazada');assert.deepEqual(await rows('#pedidos-list'),[ids[2]]);
 await run("auditFail='network'");await click(`[data-pedido-id="${ids[2]}"] button`);await idle();
 assert.equal(await text('flash-kitchen'),'Fallo de red controlado');
 await run("auditFail='load'");const before=await reads();await click('#actualizar-pedidos');await idle();
 assert.equal(await reads(),before+1);assert.equal(await text('flash-kitchen'),'Fallo de lectura controlado');
 await run("auditFail='catalog'");await click('#actualizar-pedidos');await idle();
 assert.equal(await run(`document.querySelector('[data-pedido-id="${ids[1]}"] [data-pedido-items]').textContent.includes('Producto #')`),true);
 await run("auditFail='';auditEmpty=true");await click('#actualizar-pedidos');await idle();
 assert.match(await text('pedidos-list'),/No hay pedidos activos/);
 assert.match(await text('pedidos-historial'),/No hay pedidos en el historial/);
 assert.equal(await run("document.querySelectorAll('[data-pedido-id]').length"),0);
 await run("auditEmpty=false");await click('#actualizar-pedidos');await idle();
 await click(`[data-pedido-id="${ids[2]}"] button`);await idle();
 assert.match(await text('pedidos-list'),/No hay pedidos activos/);
 assert.equal((await rows('#pedidos-historial')).length,3);
 console.log('Kitchen browser: classification, transitions, CSRF, details, errors, refresh and responsive OK');
 ws.close();clearTimeout(deadline);
})().catch(e=>{console.error(e);process.exit(1);});
"""
    script = script.replace("IDS", str(ids)).replace("FALLBACK", str(fallback_id))
    server = make_server("127.0.0.1", 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = tmp_path / "browser-profile"
    process = subprocess.Popen([
        browser, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", "--disable-background-networking",
        "--remote-debugging-port=0", f"--user-data-dir={profile}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        port_file = profile / "DevToolsActivePort"
        port = None
        for _ in range(200):
            try:
                port = port_file.read_text().splitlines()[0]
                break
            except (OSError, IndexError):
                if process.poll() is not None:
                    break
                time.sleep(.05)
        assert port, "Chromium no habilito CDP"
        result = subprocess.run([
            node, "-e", script, port, f"http://127.0.0.1:{server.server_port}",
            str(tmp_path / "kitchen-desktop.png"), "kitchen",
        ], capture_output=True, text=True, encoding="utf-8", timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Kitchen browser:" in result.stdout
        print("Kitchen captures:", tmp_path)
        db.session.expire_all()
        assert db.session.get(Pedido, ids[1]).estado_preparacion == "LISTO_PARA_SERVIR"
        assert db.session.get(Pedido, ids[2]).estado_preparacion == "LISTO_PARA_SERVIR"
        assert db.session.get(Pedido, ids[3]).estado_preparacion == "NO_ENVIADO"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        server.shutdown()
        thread.join(timeout=5)
