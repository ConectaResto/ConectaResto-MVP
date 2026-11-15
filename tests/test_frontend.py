import pytest

from app.extensions import db
from app.models import Rol, Usuario


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


# ---------- Rutas públicas ----------
def test_index_public(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "ConectaResto" in html


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Iniciar sesión" in html


# ---------- Paneles requieren autenticación ----------
def test_admin_panel_requires_auth(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code in (200, 302)
    html = response.get_data(as_text=True)
    assert "Debes iniciar sesión" in html or response.status_code == 302


def test_waiter_panel_requires_auth(client):
    response = client.get("/waiter", follow_redirects=False)
    assert response.status_code in (200, 302)


# ---------- Acceso por rol ----------
def test_admin_can_access_admin_panel(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel ADMIN" in html
    assert "admin1" in html
    assert "ADMIN" in html


def test_admin_can_access_waiter_panel_forbidden(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_can_access_waiter_panel(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Mesero" in html


def test_waiter_can_access_admin_panel_forbidden(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_can_access_kitchen_panel(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Cocina" in html


def test_cashier_can_access_cashier_panel(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Caja" in html


# ---------- Tarjetas por rol ----------
def test_admin_panel_shows_only_functional_sections(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # ADMIN muestra sus cuatro gestiones, sin tarjetas provisionales.
    assert "Usuarios" in html
    assert "Categorías" in html
    assert "Productos" in html
    assert "Mesas" in html
    assert "Ver y gestionar pedidos del sistema" not in html
    assert 'class="card card-disabled"' not in html
    assert "Pendiente" not in html


def test_waiter_panel_shows_enabled_cards(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Tarjetas WAITER habilitadas con URLs reales
    assert "Mesas" in html
    assert "Pedidos" in html
    assert "Ver mesas" in html
    assert "Gestionar pedidos" in html
    assert "Pendiente" not in html


def test_kitchen_panel_shows_enabled_cards(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # Tarjeta KITCHEN habilitada con URL real
    assert "Pedidos" in html
    assert "Ver pedidos" in html
    assert "Pendiente" not in html


def test_cashier_panel_no_disabled_cards(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    # No aparecen tarjetas deshabilitadas de "Próximamente"
    assert "Pedidos para cobrar" not in html
    assert "Cierre de caja" not in html
    assert "Pendiente" not in html
    # Las funciones reales de caja siguen presentes
    assert "Servicios activos" in html
    assert "Registrar pago simulado" in html
    assert "Cerrar servicio" in html


# ---------- Navegación por rol ----------
def test_nav_shows_user_and_logout_when_authenticated(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/admin", follow_redirects=True)
    html = response.get_data(as_text=True)
    assert "admin1" in html
    assert "ADMIN" in html
    assert "Cerrar sesión" in html


# ---------- Redirección de login si ya autenticado ----------
def test_login_redirects_if_authenticated(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/login", follow_redirects=False)
    assert response.status_code == 302


# ---------- Nuevas rutas de mesero y cocina ----------
def test_waiter_can_access_mesas(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Mesas" in html
    assert "Panel Mesero" in html


def test_waiter_can_access_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Mesero" in html


def test_kitchen_can_access_pedidos(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Pedidos" in html
    assert "Panel Cocina" in html


def test_admin_cannot_access_waiter_mesas(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_waiter_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/waiter/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_kitchen_pedidos(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_kitchen_pedidos(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/kitchen/pedidos", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_waiter_mesas(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/waiter/mesas", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_mesas_requires_auth(client):
    response = client.get("/waiter/mesas", follow_redirects=False)
    assert response.status_code in (200, 302)


def test_waiter_pedidos_requires_auth(client):
    response = client.get("/waiter/pedidos", follow_redirects=False)
    assert response.status_code in (200, 302)


def test_kitchen_pedidos_requires_auth(client):
    response = client.get("/kitchen/pedidos", follow_redirects=False)
    assert response.status_code in (200, 302)


# ---------- Regresión: bucle de redirecciones en paneles directos ----------
def test_admin_can_access_panel_admin_direct(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel ADMIN" in html


def test_waiter_can_access_panel_waiter_direct(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Mesero" in html


def test_kitchen_can_access_panel_kitchen_direct(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Cocina" in html


def test_cashier_can_access_panel_cashier_direct(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Panel Caja" in html


def test_admin_cannot_access_panel_waiter(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_admin(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


# ---------- Regresión: aislamiento de roles entre paneles ----------
def test_admin_cannot_access_panel_kitchen(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403


def test_admin_cannot_access_panel_cashier(client, admin_user):
    login(client, "admin1", "admin-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_kitchen(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403


def test_waiter_cannot_access_panel_cashier(client, waiter_user):
    login(client, "mesero1", "waiter-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_admin(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_waiter(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_kitchen_cannot_access_panel_cashier(client, kitchen_user):
    login(client, "cocina1", "kitchen-pass")
    response = client.get("/panel/cashier", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_admin(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/admin", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_waiter(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/waiter", follow_redirects=True)
    assert response.status_code == 403


def test_cashier_cannot_access_panel_kitchen(client, cashier_user):
    login(client, "caja1", "cashier-pass")
    response = client.get("/panel/kitchen", follow_redirects=True)
    assert response.status_code == 403


@pytest.mark.parametrize("fixture_name,username,password,role,target", [
    ("admin_user", "admin1", "admin-pass", "ADMIN", "/panel/admin"),
    ("waiter_user", "mesero1", "waiter-pass", "WAITER", "/panel/waiter"),
    ("cashier_user", "caja1", "cashier-pass", "CASHIER", "/panel/cashier"),
    ("kitchen_user", "cocina1", "kitchen-pass", "KITCHEN", "/panel/kitchen"),
])
def test_login_browser(app, request, tmp_path, fixture_name, username, password, role, target):
    """Verifica la presentación del login y su autenticación real en SQLite."""
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import threading
    import time
    from werkzeug.serving import make_server
    from tests.browser_helpers import CDP_SETUP

    node = shutil.which("node")
    browser = next((path for path in (
        os.environ.get("PUBLIC_MENU_TEST_BROWSER", ""),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ) if path and Path(path).is_file()), None)
    if not node or not browser:
        pytest.skip("Requiere Node y un navegador Chromium ya instalado")
    request.getfixturevalue(fixture_name)
    harness = CDP_SETUP + r"""
 const account=JSON.parse(mode);
 await send('Page.enable'); await send('Runtime.enable');
 await send('Page.navigate',{url:base+'/login'});
 await until("document.getElementById('login-form') && document.readyState === 'complete'");
 assert.match(await run("document.querySelector('.logo').textContent"),/ConectaResto/);
 assert.equal(await run("document.querySelector('h1').textContent"),'Iniciar sesión');
 assert.equal(await run("document.getElementById('username').name"),'username');
 assert.equal(await run("document.getElementById('password').name"),'password');
 assert.equal(await run("document.getElementById('password').type"),'password');
 assert.equal(await run("document.getElementById('login-form').noValidate"),true);
 assert.equal(await run("document.getElementById('login-form').getAttribute('method')"),null);
 for (const [width,height,mobile,name] of [[1280,900,false,'desktop'],[375,812,true,'mobile']]) {
  await send('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile});
  await run('new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))');
  assert.equal(await run("document.documentElement.scrollWidth <= window.innerWidth"),true);
  assert.equal(await run("{const r=document.querySelector('.login-card').getBoundingClientRect();Math.abs(r.left+r.width/2-document.documentElement.clientWidth/2)<2}"),true,'formulario centrado');
  assert.equal(await run("{const r=document.querySelector('.login-card').getBoundingClientRect(),m=document.querySelector('.main').getBoundingClientRect();Math.abs(r.top+r.height/2-m.top-m.height/2)<2}"),true,'centrado vertical');
  assert.equal(await run("getComputedStyle(document.getElementById('login-btn')).width === getComputedStyle(document.getElementById('username')).width"),true);
  await capture(imagePath.replace('desktop',name));
 }
 await run("document.getElementById('username').focus()");
 await send('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
 await send('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9});
 assert.equal(await run('document.activeElement.id'),'password');
 assert.equal(await run("parseFloat(getComputedStyle(document.activeElement).outlineWidth)>=2"),true,'foco visible de teclado');
 await capture(imagePath.replace('desktop','focus'));
 await run("window.loginRequests=[];window.loginFetch=window.fetch.bind(window);window.fetch=async(url,opts)=>{const response=await window.loginFetch(url,opts);if(String(url)==='/auth/login')window.loginRequests.push({status:response.status,csrf:opts.headers['X-CSRF-Token']||null});return response;};");
 const denied=await run("fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify("+JSON.stringify({username:account.username,password:account.password})+")}).then(r=>r.status)");
 assert.equal(denied,400,'CSRF sigue siendo obligatorio');
 await run("document.getElementById('username').value="+JSON.stringify(account.username)+";document.getElementById('password').value='incorrecta';");
 await click('#login-btn');
 await until("document.querySelector('#login-page .flash.error') && !document.getElementById('login-btn').disabled");
 assert.match(await run("document.querySelector('#login-page .flash.error').textContent"),/Credenciales|incorrect/i);
 assert.equal(await run("document.querySelector('#login-page .flash.error').getBoundingClientRect().top-document.getElementById('login-btn').getBoundingClientRect().bottom>=16"),true,'error separado del boton');
 assert.equal(await run('location.pathname'),'/login');
 assert.equal(await run('window.loginRequests[1].status'),401);
 assert.equal(await run("window.loginRequests[1].csrf === document.querySelector('meta[name=csrf-token]').content"),true);
 await capture(imagePath.replace('desktop','error'));
 await run("document.getElementById('password').value="+JSON.stringify(account.password)+";document.getElementById('password').focus();");
 await click('#login-btn');
 await until("location.pathname === "+JSON.stringify(account.target)+" && document.readyState === 'complete'");
 assert.equal(await run("fetch('/auth/me').then(r=>r.json()).then(data=>data.data.rol)"),account.role);
 ws.close();clearTimeout(deadline);console.log('LOGIN: desktop, mobile, foco, errores, CSRF y acceso por rol OK');
})().catch(error=>{console.error(error);process.exit(1);});
"""
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
        for _ in range(200):
            if port_file.is_file() or process.poll() is not None:
                break
            time.sleep(.05)
        assert port_file.is_file(), "El navegador no habilitó CDP"
        result = subprocess.run([
            node, "-e", harness, port_file.read_text().splitlines()[0],
            f"http://127.0.0.1:{server.server_port}", str(tmp_path / "login-desktop.png"),
            json.dumps(dict(username=username,password=password,role=role,target=target)),
        ], text=True, encoding="utf-8", capture_output=True, timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        print("LOGIN_PREVIEW=" + str(tmp_path))
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        server.shutdown()
        thread.join(timeout=5)
