"""HTTP and real-browser checks for the standalone public client interface.

Browser checks use an already installed Chromium browser and Node's built-in
CDP WebSocket client. No browser framework or package is installed by tests.
"""

import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

import pytest
from werkzeug.serving import make_server

from tests.browser_helpers import CDP_SETUP

from app.extensions import db
from app.models import Category, Mesa, Pedido, Product, Rol, Servicio, Usuario


@pytest.fixture
def menu_context(app):
    mesa = Mesa(numero=7, estado="OCUPADA", public_token="a" * 64)
    inactive = Mesa(numero=8, public_token="b" * 64)
    closed = Mesa(numero=9, estado="CERRADA", public_token="c" * 64)
    category = Category(name="Bebidas")
    food = Category(name="Comida")
    waiter = Usuario(username="menu-waiter", email="menu@test.invalid", rol=Rol(name="WAITER"))
    waiter.set_password("test-password")
    db.session.add_all([mesa, inactive, closed, category, food, waiter])
    db.session.flush()
    product = Product(name="Café", description="Recién preparado", price="12.35", categoria_id=category.id)
    snack = Product(name="Pan", description='<img src=x onerror="window.badContent=true">', price="0.10", categoria_id=food.id)
    hidden = Product(name="No disponible", price="1.00", categoria_id=category.id, is_available=False)
    db.session.add_all([product, snack, hidden, Servicio(mesa_id=mesa.id, abierto_por_id=waiter.id)])
    db.session.commit()
    return mesa, product


def test_public_page_uses_separate_assets_and_no_login(client, menu_context):
    mesa, _ = menu_context
    response = client.get(f"/public/mesas/{mesa.public_token}/menu")
    text = response.get_data(as_text=True)
    assert response.status_code == 200
    for content in ('Mesa 7', 'public_menu.css', 'public_menu.js', 'data-csrf-url="/auth/csrf"',
                    'action="pedidos"', 'Confirmar y enviar', 'Total estimado'):
        assert content in text
    assert mesa.public_token not in text
    assert 'app.js' not in text and '/login' not in text
    assert 'Set-Cookie' not in response.headers


@pytest.mark.parametrize("path", ["/static/js/public_menu.js", "/static/css/public_menu.css"])
def test_public_assets_are_available_without_login(client, path):
    assert client.get(path).status_code == 200


def test_invalid_token_never_renders_order_form(client):
    response = client.get('/public/mesas/invalid/menu')
    assert response.status_code == 404
    assert b'order-form' not in response.data


def test_order_contract_preserves_csrf_and_empty_cart_validation(client, menu_context):
    mesa, _ = menu_context
    path = f"/public/mesas/{mesa.public_token}/pedidos"
    assert client.post(path, json={"items": []}).status_code == 400
    csrf = client.get('/auth/csrf').json['data']['csrf_token']
    assert client.post(path, json={"items": []}, headers={'X-CSRF-Token': csrf}).status_code == 400
    assert Pedido.query.count() == 0


# This runs the actual JavaScript in a browser against the real Flask app.
# DOM interactions, injected failures and assertions are kept in this test file.
BROWSER_CHECK = CDP_SETUP + r""" const navigate=async token=>{const path='/public/mesas/'+token.repeat(64)+'/menu';await send('Page.navigate',{url:base+path});await until(`location.pathname === ${JSON.stringify(path)} && document.readyState === 'complete' && document.querySelectorAll('.product-card').length === 2`);};
 const review=async()=>{await click('#review-order');await until("!document.getElementById('order-review').hidden");};
 const waitDone=()=>until("document.getElementById('order-form').getAttribute('aria-busy') === 'false' && document.getElementById('order-status').textContent !== 'Preparando el envío…'");
 await send('Page.enable'); await send('Runtime.enable');
 await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
 await navigate('a');
 if(mode === 'quantity-regression') {
  await run("window.quantityPosts=0;window.quantityFetch=window.fetch.bind(window);window.fetch=(url,opts)=>{if(opts?.method==='POST')window.quantityPosts++;return window.quantityFetch(url,opts);}");
  const edit=quantity=>run(`{const i=document.querySelector('[data-quantity]');i.value=${JSON.stringify(quantity)};i.dispatchEvent(new Event('input',{bubbles:true}));}`);
  const assertInvalid=async()=>{
   assert.equal(await run("document.querySelector('[data-quantity]').value"),'0');
   assert.equal(await run("document.querySelector('[data-quantity]').getAttribute('aria-invalid')"),'true');
   assert.equal(await run("document.getElementById('review-order').disabled"),true);
   assert.match(await text('order-status'),/Corrige las cantidades/);
   assert.match(await text('cart-total'),/Revisa cantidades/);
   assert.match(await run("document.querySelector('.cart-line').textContent"),/cantidad entera positiva/);
   await run("document.getElementById('order-form').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));document.getElementById('send-order').click();");
   assert.equal(await run("document.getElementById('order-review').hidden"),true);
   assert.equal(await run('window.quantityPosts'),0,'invalid quantities must never send a POST');
  };
  await click('.product-card button');await edit('0');
  // A = 0, then add B: preserve the visible draft and its error state.
  await run("document.querySelectorAll('.product-card button')[1].click()");
  await assertInvalid();await capture(imagePath.replace('mobile','invalid-add'));
  // A = 0, then remove B: the error must remain understandable.
  await click('.cart-line:nth-child(2) button');
  await assertInvalid();await capture(imagePath.replace('mobile','invalid-remove'));
  // Correcting A to 2 synchronizes the draft, numeric quantity and validation.
  await edit('2');
  assert.equal(await run("document.querySelector('[data-quantity]').getAttribute('aria-invalid')"),'false');
  assert.equal(await run("document.getElementById('review-order').disabled"),false);
  assert.match(await text('cart-total'),/24,70/);
  assert.match(await run("document.querySelector('.cart-line').textContent"),/Subtotal: 24,70/);
  await review();assert.match(await text('review-items'),/2 × Café/);
  assert.equal(await run('window.quantityPosts'),0);
  await capture(imagePath.replace('mobile','corrected'));
  ws.close();clearTimeout(deadline);console.log('Browser UI: quantity regression OK — invalid A survives adding/removing B, correction to 2 enables review, no invalid POST');return;
 }
 assert.equal(await run("document.getElementById('review-order').disabled"),true,'empty cart');
 assert.equal(await run("document.documentElement.scrollWidth <= window.innerWidth"),true,'mobile overflow');
 await run("document.querySelector('[data-category=\"1\"]').textContent='C'.repeat(100);document.querySelector('#catalog > section > h3').textContent='C'.repeat(100);");
 assert.equal(await run("document.documentElement.scrollWidth <= window.innerWidth"),true,'long category overflow');
 await run("document.querySelector('[data-category=\"1\"]').textContent='Bebidas';document.querySelector('#catalog > section > h3').textContent='Bebidas';");
 assert.equal(await run("document.querySelectorAll('.product-card img').length"),0,'unsafe HTML');
 assert.match(await run("document.querySelectorAll('.product-card')[1].textContent"),/img src=x/);
 await click('[data-category="1"]');
 assert.equal(await run("[...document.querySelectorAll('#catalog > section')].filter(s=>!s.hidden).length"),1);
 await click('[data-category="null"]');
 await click('.product-card button'); await click('.product-card button');
 assert.match(await text('cart-total'),/24,70/);
 for(const value of ['0','-1','1.5','','2147483648']) {
  await run(`{const i=document.querySelector('[data-quantity]');i.value=${JSON.stringify(value)};i.dispatchEvent(new Event('input',{bubbles:true}));}`);
  assert.equal(await run("document.getElementById('review-order').disabled"),true,'invalid '+value);
 }
 await run("{const i=document.querySelector('[data-quantity]');i.value='3';i.dispatchEvent(new Event('input',{bubbles:true}));}");
 assert.match(await text('cart-total'),/37,05/);
 await click('.cart-controls button');
 assert.equal(await run("document.getElementById('review-order').disabled"),true,'removed');
 await click('.product-card button');
 // Only GET CSRF is allowed before explicit confirmation; count actual POSTs.
 await run("window.realFetch=window.fetch.bind(window);window.postCount=0;window.fetch=(url,opts)=>{if(opts?.method==='POST')window.postCount++;return window.realFetch(url,opts);}");
 await review(); assert.equal(await run('window.postCount'),0);
 await click('#cancel-review'); assert.equal(await run('window.postCount'),0);
 // HTTP rejections and network errors preserve the cart.
 for(const [code,message] of [[409,'La mesa no tiene servicio activo'],[404,'Producto no encontrado'],[400,'Token CSRF invalido'],[500,'Error interno']]) {
  await run(`window.fetch=(url,opts)=>opts?.method==='POST'?(window.postCount++,Promise.resolve(new Response(JSON.stringify({success:false,error:${JSON.stringify(message)}}),{status:${code},headers:{'Content-Type':'application/json'}}))):window.realFetch(url,opts);`);
  await review(); await click('#send-order'); await waitDone();
  assert.equal(await run("document.querySelectorAll('.cart-line').length"),1,'cart kept '+code);
  assert.match(await text('order-status'),code>=500?/Consulta al mesero/:new RegExp(message));
 }
 await run("window.fetch=(url,opts)=>opts?.method==='POST'?(window.postCount++,Promise.reject(new Error('offline'))):window.realFetch(url,opts);");
 await review(); const count=await run('window.postCount'); await click('#send-order');await waitDone();
 await new Promise(r=>setTimeout(r,250));assert.equal(await run('window.postCount'),count+1,'no automatic retry');
 assert.match(await text('order-status'),/evitar duplicados/);
 assert.equal(await run("document.querySelectorAll('.cart-line').length"),1);
 // CSRF failure stops before the POST.
 await run("window.fetch=(url,opts)=>String(url).includes('/auth/csrf')?Promise.reject(new Error('offline')):window.realFetch(url,opts);");
 await review();await click('#send-order');await waitDone();assert.equal(await run('window.postCount'),count+1);
 // A real anonymous order; a delayed request makes double-click deterministic.
 await run("window.postCount=0;window.fetch=async(url,opts)=>{if(opts?.method==='POST'){window.postCount++;await new Promise(r=>setTimeout(r,150));}return window.realFetch(url,opts);}");
 await review();await run("document.getElementById('send-order').click();document.getElementById('send-order').click();");
 await until("document.getElementById('order-status').dataset.kind === 'success'");
 assert.equal(await run('window.postCount'),1);
 assert.match(await text('order-status'),/Pedido #\d+ recibido\. Estado: PENDIENTE/);
 assert.equal(await run("document.querySelectorAll('.cart-line').length"),0);
 assert.equal(await run("fetch('/auth/me').then(r=>r.status)"),401,'no login');
 // Live backend rejections for missing service and closed table.
 for(const [token,message] of [['b','servicio activo'],['c','mesa esta cerrada']]) {
  await navigate(token);await click('.product-card button');await review();await click('#send-order');await waitDone();
  assert.match(await text('order-status'),new RegExp(message,'i'));
  assert.equal(await run("document.querySelectorAll('.cart-line').length"),1);
 }
 // Show a normal mobile cart for visual inspection, then check desktop overflow.
 await navigate('a');await click('.product-card button');
 await capture(imagePath);
 await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
 assert.equal(await run("document.documentElement.scrollWidth <= window.innerWidth"),true,'desktop overflow');
 await capture(imagePath.replace('mobile','desktop'));
 ws.close();clearTimeout(deadline);console.log('Browser UI: categories, safe text, quantities, totals, confirmation, CSRF, double-click, HTTP errors, offline, live orders, mobile/desktop OK');
})().catch(e=>{console.error(e);process.exit(1);});
"""


@pytest.mark.parametrize('mode', ['quantity-regression', 'full-flow'])
def test_real_browser_menu_flow(app, menu_context, tmp_path, mode):
    node = shutil.which('node')
    browser = next((path for path in (
        os.environ.get('PUBLIC_MENU_TEST_BROWSER', ''),
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    ) if path and Path(path).is_file()), None)
    if not node or not browser:
        pytest.skip('Requiere Node con WebSocket nativo y navegador Chromium ya instalado')
    server = make_server('127.0.0.1', 0, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    profile = tmp_path / 'browser-profile'
    process = subprocess.Popen([
        browser, '--headless=new', '--disable-gpu', '--no-first-run',
        '--no-default-browser-check', '--disable-background-networking',
        '--remote-debugging-port=0', f'--user-data-dir={profile}', 'about:blank',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        port_file = profile / 'DevToolsActivePort'
        for _ in range(200):
            if port_file.is_file():
                break
            if process.poll() is not None:
                pytest.fail('El navegador de pruebas terminó antes de habilitar CDP')
            time.sleep(.05)
        assert port_file.is_file(), 'El navegador no habilitó CDP'
        result = subprocess.run([
            node, '-e', BROWSER_CHECK, port_file.read_text().splitlines()[0],
            f'http://127.0.0.1:{server.server_port}', str(tmp_path / 'menu-mobile.png'),
            mode,
        ], capture_output=True, text=True, encoding='utf-8', timeout=90)
        assert result.returncode == 0, result.stdout + result.stderr
        assert 'Browser UI:' in result.stdout, result.stdout + result.stderr
        db.session.expire_all()
        assert Pedido.query.count() == (0 if mode == 'quantity-regression' else 1), 'Solo el envío confirmado debe persistir un pedido'
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        server.shutdown()
        thread.join(timeout=5)
