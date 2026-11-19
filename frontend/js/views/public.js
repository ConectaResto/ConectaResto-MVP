class PublicView {
    constructor(container) {
        this.container = container;
        this.mesaToken = null;
        this.mesaNumero = null;
        this.categories = [];
        this.products = [];
        this.cartContainer = null;
        this.cartItemsContainer = null;
        this.cartTotalEl = null;
        this.orderForm = null;
    }

    async init() {
        window.appPublic = this;
        const params = new URLSearchParams(window.location.search);
        this.mesaToken = params.get('token');

        if (!this.mesaToken) {
            this.container.innerHTML = `
                <div class="view-card">
                    <div class="view-card-header">Men&uacute; p&uacute;blico</div>
                    <div class="view-card-body text-center py-5">
                        <div class="alert alert-warning">
                            No se ha especificado un token de mesa v&aacute;lido.
                        </div>
                        <p class="text-muted">Escanea el QR de una mesa o accede mediante el enlace proporcionado.</p>
                        <p class="text-muted">Ejemplo: <code>/app/?token=TOKEN_DE_LA_MESA#public</code></p>
                    </div>
                </div>
            `;
            return;
        }

        this.container.innerHTML = `
            <div class="view-card">
                <div class="view-card-header">
                    Men&uacute; p&uacute;blico - Mesa <span id="publicMesaNumero">--</span>
                </div>
                <div class="view-card-body row">
                    <div class="col-lg-8" id="publicCatalog">
                        <div class="text-center py-4"><div class="spinner-border" role="status"></div><p class="mt-2">Cargando carta...</p></div>
                    </div>
                    <div class="col-lg-4" id="publicCart">
                        <div class="text-center py-4"><div class="spinner-border" role="status"></div><p class="mt-2">Cargando carrito...</p></div>
                    </div>
                </div>
            </div>
        `;

        try {
            const mesaData = await api.get(`/public/mesas/${this.mesaToken}`);
            this.mesaNumero = mesaData.data.numero;
            this.container.querySelector('#publicMesaNumero').textContent = this.mesaNumero;

            const [cats, prods] = await Promise.all([
                api.get('/categories'),
                api.get('/products')
            ]);
            this.categories = cats.data || [];
            this.products = (prods.data || []).filter(p => p.is_active !== false && p.is_available !== false);

            this.render();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    render() {
        const catalogEl = this.container.querySelector('#publicCatalog');
        const cartEl = this.container.querySelector('#publicCart');

        catalogEl.innerHTML = `
            <div class="mb-3">
                <button class="btn btn-outline-secondary btn-sm" data-cat="">Todas</button>
            </div>
            <div id="publicProductsGrid" class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-3"></div>
        `;

        const catButtons = document.createElement('div');
        catButtons.className = 'mb-3';
        const btnTodas = document.createElement('button');
        btnTodas.type = 'button';
        btnTodas.className = 'btn btn-outline-secondary btn-sm';
        btnTodas.textContent = 'Todas';
        btnTodas.dataset.cat = '';
        catButtons.appendChild(btnTodas);
        this.categories.forEach(c => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary btn-sm';
            btn.textContent = c.name;
            btn.dataset.cat = String(c.id);
            catButtons.appendChild(btn);
        });
        catalogEl.insertBefore(catButtons, catalogEl.firstChild);

        catButtons.querySelectorAll('[data-cat]').forEach(btn => {
            btn.addEventListener('click', () => {
                const catId = btn.dataset.cat || null;
                this.container.querySelectorAll('[data-cat]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.renderProducts(catId);
            });
        });

        cartEl.innerHTML = `
            <h6>Tu carrito</h6>
            <div id="publicCartList" class="mb-3"></div>
            <div class="d-flex justify-content-between align-items-center mb-3">
                <strong>Total:</strong>
                <strong id="publicCartTotal">${state.getCartTotal()}</strong>
            </div>
            <div class="mb-3">
                <p class="text-muted small">Los precios se validan al enviar. No se realiza pago aqu&iacute;.</p>
                <div id="publicOrderStatus" class="small"></div>
            </div>
            <button id="publicReviewBtn" class="btn btn-primary w-100" disabled>Revisar pedido</button>
            <div id="publicReviewSection" style="display:none;" class="mt-3 p-3 border rounded">
                <h6>Confirma tu pedido</h6>
                <div id="publicReviewItems"></div>
                <p>Total estimado: <strong id="publicReviewTotal"></strong></p>
                <p class="text-muted small">El pedido quedar&aacute; pendiente de atenci&oacute;n del mesero.</p>
                <div class="d-grid gap-2 mt-2">
                    <button id="publicCancelReview" class="btn btn-outline-secondary">Seguir editando</button>
                    <button id="publicSendOrder" class="btn btn-success">Confirmar y enviar</button>
                </div>
            </div>
        `;

        this.cartContainer = this.container.querySelector('#publicCartList');
        this.cartTotalEl = this.container.querySelector('#publicCartTotal');
        this.orderForm = this.container.querySelector('#publicReviewBtn');

        this.container.querySelector('#publicReviewBtn').addEventListener('click', () => this.showReview());
        this.container.querySelector('#publicCancelReview').addEventListener('click', () => this.hideReview());
        this.container.querySelector('#publicSendOrder').addEventListener('click', () => this.sendOrder());

        this.renderProducts();
        this.updateCartUI();
    }

    productCard(p) {
        const cents = parseFloat(p.price) * 100;
        const col = document.createElement('div');
        col.className = 'col';

        const card = document.createElement('div');
        card.className = 'card h-100';

        const img = document.createElement('img');
        img.className = 'card-img-top';
        img.alt = p.name;
        img.style.height = '160px';
        img.style.objectFit = 'cover';
        const imageUrl = p.image_url || '/static/img/default-product.svg';
        if (/^\/[^/]/.test(imageUrl)) {
            img.src = imageUrl;
        } else {
            img.src = '/static/img/default-product.svg';
        }

        const cardBody = document.createElement('div');
        cardBody.className = 'card-body';

        const title = document.createElement('h5');
        title.className = 'card-title';
        title.textContent = p.name;

        const desc = document.createElement('p');
        desc.className = 'card-text text-muted small';
        desc.textContent = p.description || '';

        const flex = document.createElement('div');
        flex.className = 'd-flex justify-content-between align-items-center';

        const price = document.createElement('span');
        price.className = 'fw-bold';
        price.textContent = formatMoney(cents);

        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-primary btn-sm';
        addBtn.textContent = 'Agregar';
        addBtn.addEventListener('click', () => this.addToCart(p.id));

        flex.appendChild(price);
        flex.appendChild(addBtn);
        cardBody.appendChild(title);
        cardBody.appendChild(desc);
        cardBody.appendChild(flex);
        card.appendChild(img);
        card.appendChild(cardBody);
        col.appendChild(card);

        return col;
    }

    renderProducts(catId = null) {
        const grid = this.container.querySelector('#publicProductsGrid');
        const filtered = catId === null ? this.products : this.products.filter(p => p.categoria_id == catId);
        grid.innerHTML = '';
        filtered.forEach(p => {
            grid.appendChild(this.productCard(p));
        });
    }

    addToCart(productId) {
        const product = this.products.find(p => p.id == productId);
        if (!product) return;
        const cents = parseFloat(product.price) * 100;
        state.addToCart(product.id, product.name, cents);
        flash(`${product.name} agregado al carrito.`, 'success');
        this.updateCartUI();
    }

    updateCartUI() {
        if (!this.cartContainer) return;
        const list = this.container.querySelector('#publicCartList');
        const totalEl = this.container.querySelector('#publicCartTotal');
        const reviewBtn = this.container.querySelector('#publicReviewBtn');

        if (state.cart.size === 0) {
            list.innerHTML = '<p class="text-muted small">El carrito est&aacute; vac&iacute;o.</p>';
            totalEl.textContent = state.getCartTotal();
            reviewBtn.disabled = true;
            return;
        }

        list.innerHTML = '';
        for (const [id, item] of state.cart) {
            const div = document.createElement('div');
            div.className = 'd-flex justify-content-between align-items-center border-bottom py-2';

            const info = document.createElement('div');
            const nameDiv = document.createElement('div');
            nameDiv.textContent = item.name;
            const qtyDiv = document.createElement('div');
            qtyDiv.className = 'small text-muted';
            qtyDiv.textContent = formatMoney(item.cents) + ' x ' + item.quantity;
            info.appendChild(nameDiv);
            info.appendChild(qtyDiv);

            const removeBtn = document.createElement('button');
            removeBtn.type = 'button';
            removeBtn.className = 'btn btn-sm btn-outline-danger';
            removeBtn.textContent = '&times;';
            removeBtn.addEventListener('click', () => this.removeFromCart(id));

            div.appendChild(info);
            div.appendChild(removeBtn);
            list.appendChild(div);
        }
        totalEl.textContent = state.getCartTotal();
        reviewBtn.disabled = false;
    }

    showReview() {
        const section = this.container.querySelector('#publicReviewSection');
        const items = this.container.querySelector('#publicReviewItems');
        const total = this.container.querySelector('#publicReviewTotal');
        items.innerHTML = '';
        for (const [id, item] of state.cart) {
            const div = document.createElement('div');
            div.className = 'd-flex justify-content-between mb-1';
            const qtySpan = document.createElement('span');
            qtySpan.textContent = item.quantity + ' x ' + item.name;
            const priceSpan = document.createElement('span');
            priceSpan.textContent = formatMoney(item.cents * item.quantity);
            div.appendChild(qtySpan);
            div.appendChild(priceSpan);
            items.appendChild(div);
        }
        total.textContent = state.getCartTotal();
        section.style.display = 'block';
        this.container.querySelector('#publicReviewBtn').style.display = 'none';
    }

    hideReview() {
        this.container.querySelector('#publicReviewSection').style.display = 'none';
        this.container.querySelector('#publicReviewBtn').style.display = 'block';
    }

    async sendOrder() {
        const btn = this.container.querySelector('#publicSendOrder');
        btn.disabled = true;
        btn.textContent = 'Enviando...';

        const items = [...state.cart.values()].map(item => ({
            producto_id: item.id,
            cantidad: item.quantity
        }));

        try {
            const data = await api.post(`/public/mesas/${this.mesaToken}/pedidos`, { items });
            flash(`Pedido #${data.data.id} recibido. Estado: ${estadoLegible(data.data.estado)}.`, 'success');
            state.clearCart();
            this.hideReview();
            this.container.querySelector('#publicReviewBtn').style.display = 'block';
            this.updateCartUI();
            this.container.querySelector('#publicOrderStatus').textContent = `Pedido #${data.data.id} enviado.`;
        } catch (err) {
            flash(err.message, 'danger');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Confirmar y enviar';
        }
    }

    removeFromCart(productId) {
        state.removeFromCart(productId);
        this.updateCartUI();
    }

    destroy() {}
}

window.appPublic = null;