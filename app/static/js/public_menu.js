(() => {
    'use strict';
    const root = document.getElementById('public-menu');
    if (!root) return;
    const byId = (id) => document.getElementById(id);
    const form = byId('order-form');
    const cart = new Map();
    let pending = false;
    let loaded = false;

    // All catalog content is inserted as text, never interpreted as HTML.
    function element(tag, text, className) {
        const node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (className) node.className = className;
        return node;
    }
    function priceInCents(price) {
        if (typeof price !== 'string' || !/^\d+(?:\.\d{1,2})?$/.test(price)) {
            throw new Error('El menú contiene un precio inválido. Consulta al mesero.');
        }
        const [whole, fraction = ''] = price.split('.');
        return BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
    }
    function money(cents) {
        return `${(cents / 100n).toLocaleString('es')},${String(cents % 100n).padStart(2, '0')}`;
    }
    function total() {
        return [...cart.values()].reduce((sum, item) => sum + item.cents * BigInt(item.quantity), 0n);
    }
    function validCart() {
        return cart.size > 0 && [...cart.values()].every((item) => !item.invalid);
    }
    function status(text, kind = '') {
        if (cart.size && !validCart()) {
            text = 'Corrige las cantidades del carrito antes de continuar.';
            kind = 'error';
        }
        byId('order-status').textContent = text;
        byId('order-status').dataset.kind = kind;
    }
    function updateControls() {
        byId('review-order').disabled = pending || !validCart();
        root.querySelectorAll('[data-cart-control]').forEach((node) => { node.disabled = pending; });
        byId('cancel-review').disabled = pending;
        byId('send-order').disabled = pending || !validCart();
        byId('send-order').textContent = pending ? 'Enviando…' : 'Confirmar y enviar';
        form.setAttribute('aria-busy', String(pending));
    }
    function changed() {
        byId('order-review').hidden = true;
        byId('cart-total').textContent = cart.size && !validCart() ? 'Revisa cantidades' : money(total());
        updateControls();
    }
    function renderCart() {
        const list = byId('cart-items');
        list.replaceChildren();
        byId('cart-empty').hidden = cart.size !== 0;
        for (const [id, item] of cart) {
            const line = element('li', undefined, 'cart-line');
            line.append(element('strong', item.name), element('p', `Precio unitario: ${money(item.cents)}`));
            const controls = element('div', undefined, 'cart-controls');
            const label = element('label', 'Cantidad ');
            const input = document.createElement('input');
            input.type = 'number'; input.min = '1'; input.max = '2147483647'; input.step = '1';
            input.required = true; input.inputMode = 'numeric'; input.value = item.quantityInput;
            input.dataset.cartControl = ''; input.dataset.quantity = String(id);
            input.setAttribute('aria-label', `Cantidad de ${item.name}`);
            const subtotal = element('p');
            function updateQuantityLine() {
                input.setAttribute('aria-invalid', String(item.invalid));
                subtotal.textContent = item.invalid ? 'Introduce una cantidad entera positiva válida.' : `Subtotal: ${money(item.cents * BigInt(item.quantity))}`;
            }
            updateQuantityLine();
            input.addEventListener('input', () => {
                if (pending) return;
                item.quantityInput = input.value;
                const quantity = Number(input.value);
                item.invalid = !/^\d+$/.test(input.value) || !Number.isInteger(quantity) || quantity < 1 || quantity > 2147483647;
                if (!item.invalid) item.quantity = quantity;
                updateQuantityLine();
                status('Carrito actualizado.');
                changed();
            });
            label.append(input);
            const remove = element('button', 'Quitar');
            remove.type = 'button'; remove.dataset.cartControl = '';
            remove.setAttribute('aria-label', `Quitar ${item.name}`);
            remove.addEventListener('click', () => {
                if (pending) return;
                cart.delete(id); renderCart(); status('Producto quitado del carrito.');
            });
            controls.append(label, remove); line.append(controls, subtotal); list.append(line);
        }
        changed();
    }
    function addProduct(product) {
        if (pending) return;
        const item = cart.get(product.id);
        if (item && (item.invalid || item.quantity >= 2147483647)) {
            status('Revisa la cantidad de este producto en el carrito.', 'error'); return;
        }
        if (item) {
            item.quantity += 1;
            item.quantityInput = String(item.quantity);
        } else cart.set(product.id, {name: product.name, cents: product.cents, quantity: 1, quantityInput: '1', invalid: false});
        renderCart(); status(`${product.name} agregado al carrito.`);
    }
    async function readJSON(response) {
        const body = await response.json();
        if (!response.ok || body.success !== true) throw new Error(body.error || 'No se pudo completar la solicitud.');
        return body.data;
    }
    async function loadCatalog() {
        if (loaded) return;
        byId('retry-catalog').hidden = true;
        byId('catalog-status').textContent = 'Cargando el menú…';
        try {
            const [categories, products] = await Promise.all([
                fetch(root.dataset.categoriesUrl, {credentials: 'same-origin'}).then(readJSON),
                fetch(root.dataset.productsUrl, {credentials: 'same-origin'}).then(readJSON),
            ]);
            if (!Array.isArray(categories) || !Array.isArray(products)) throw new Error('No se pudo leer el menú.');
            const priced = products.map((product) => ({...product, cents: priceInCents(product.price)}));
            const catalog = byId('catalog'); const nav = byId('category-nav');
            catalog.replaceChildren(); nav.replaceChildren();
            const sections = [];
            function filter(categoryId) {
                sections.forEach(({id, node}) => { node.hidden = categoryId !== null && categoryId !== id; });
                nav.querySelectorAll('button').forEach((button) => {
                    button.setAttribute('aria-pressed', String(button.dataset.category === String(categoryId)));
                });
            }
            function categoryButton(name, id) {
                const button = element('button', name); button.type = 'button'; button.dataset.category = String(id);
                button.addEventListener('click', () => filter(id)); nav.append(button);
            }
            categoryButton('Todas', null);
            for (const category of categories) {
                const section = element('section'); section.append(element('h3', category.name));
                const group = element('div', undefined, 'product-grid');
                const matching = priced.filter((product) => product.categoria_id === category.id);
                for (const product of matching) {
                    const card = element('article', undefined, 'product-card');
                    const img = element('img');
                    img.src = product.image_url || '/static/img/default-product.svg';
                    img.alt = product.name;
                    img.loading = 'lazy';
                    card.append(img, element('h3', product.name), element('p', product.description || '', 'description'), element('p', money(product.cents), 'price'));
                    const add = element('button', 'Agregar al carrito'); add.type = 'button'; add.dataset.cartControl = '';
                    add.setAttribute('aria-label', `Agregar ${product.name} al carrito`);
                    add.addEventListener('click', () => addProduct(product)); card.append(add); group.append(card);
                }
                if (!matching.length) group.append(element('p', 'No hay productos disponibles en esta categoría.'));
                section.append(group); catalog.append(section); sections.push({id: category.id, node: section});
                categoryButton(category.name, category.id);
            }
            filter(null); loaded = true;
            byId('catalog-status').textContent = priced.length ? 'Selecciona productos para tu pedido.' : 'No hay productos disponibles por ahora. Consulta al mesero.';
            updateControls();
        } catch (_) {
            byId('catalog-status').textContent = 'No pudimos cargar el menú. Revisa tu conexión o consulta al mesero.';
            byId('retry-catalog').hidden = false;
        }
    }
    byId('retry-catalog').addEventListener('click', loadCatalog);
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        if (pending || !validCart()) { if (!pending) status('Agrega productos y revisa las cantidades antes de continuar.', 'error'); return; }
        const summary = byId('review-items'); summary.replaceChildren();
        for (const item of cart.values()) summary.append(element('li', `${item.quantity} × ${item.name} — ${money(item.cents * BigInt(item.quantity))}`));
        byId('review-total').textContent = money(total());
        byId('order-review').hidden = false; status('Revisa tu pedido. Todavía no se ha enviado.');
        byId('review-title').focus();
    });
    byId('cancel-review').addEventListener('click', () => {
        if (pending) return;
        byId('order-review').hidden = true; byId('review-order').focus();
    });
    byId('send-order').addEventListener('click', async () => {
        if (pending || !validCart() || byId('order-review').hidden) return;
        pending = true; updateControls(); status('Preparando el envío…');
        let attempted = false;
        try {
            const csrf = await fetch(root.dataset.csrfUrl, {credentials: 'same-origin', cache: 'no-store'}).then(readJSON);
            if (!csrf || typeof csrf.csrf_token !== 'string' || !csrf.csrf_token) throw new Error('No pudimos preparar el envío. Inténtalo de nuevo cuando tengas conexión.');
            const items = [...cart].map(([id, item]) => ({producto_id: id, cantidad: item.quantity}));
            attempted = true;
            const response = await fetch(form.action, {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf.csrf_token},
                body: JSON.stringify({items}),
            });
            if (response.status >= 500) throw new Error('No pudimos confirmar el envío. Consulta al mesero antes de volver a enviar para evitar duplicados.');
            const body = await response.json();
            if (!response.ok || body.success !== true) {
                const message = body.error || 'El pedido fue rechazado.';
                status(`${message} El carrito se conserva. Revisa los productos o consulta al mesero.`, 'error'); return;
            }
            if (response.status !== 201 || !Number.isInteger(body.data?.id) || body.data.id < 1 || typeof body.data.estado !== 'string') throw new Error('Respuesta de confirmación inválida.');
            cart.clear(); renderCart();
            status(`Pedido #${body.data.id} recibido. Estado: ${body.data.estado}. El mesero atenderá tu pedido.`, 'success');
            byId('order-status').focus();
        } catch (_) {
            status(attempted ? 'No pudimos confirmar el envío. El carrito se conserva. Consulta al mesero antes de volver a enviar para evitar duplicados.' : 'No pudimos preparar el envío. El carrito se conserva. Revisa tu conexión e inténtalo de nuevo.', 'error');
        } finally {
            pending = false; byId('order-review').hidden = true; updateControls();
        }
    });
    renderCart(); loadCatalog();
})();
