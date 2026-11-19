class WaiterView {
    constructor(container) {
        this.container = container;
        this.mesas = [];
        this.servicios = [];
        this.pedidos = [];
        this.productos = [];
        this.pedidoItems = [];
        this.activeTab = 'mesas';
    }

    async init() {
        window.appWaiter = this;
        this.container.innerHTML = `
            <div class="view-card">
                <div class="view-card-header">Panel Mesero</div>
                <div class="view-card-body">
                    <ul class="nav nav-tabs mb-3" id="waiterTabs">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#waiterMesas">Mesas y Servicios</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#waiterPedidos">Pedidos</button></li>
                    </ul>
                    <div class="tab-content" id="waiterTabContent">
                        <div class="tab-pane fade show active" id="waiterMesas"></div>
                        <div class="tab-pane fade" id="waiterPedidos"></div>
                    </div>
                </div>
            </div>
        `;

        this.container.querySelectorAll('#waiterTabs button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.dataset.bsTarget.replace('#', '');
                this.activeTab = target;
                this.loadTab(target);
            });
        });

        await this.loadTab('mesas');
    }

    async loadTab(tab) {
        const container = this.container.querySelector(`#waiter${tab}`);
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border" role="status"></div></div>';

        try {
            if (tab === 'mesas') await this.renderMesasTab(container);
            if (tab === 'pedidos') await this.renderPedidosTab(container);
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async renderMesasTab(container) {
        await this.loadMesas();
        await this.loadServicios();

        container.innerHTML = `
            <h5>Mesas</h5>
            <div class="table-responsive mb-3">
                <table class="table table-sm align-middle" id="waiterMesasTable">
                    <thead><tr><th>N&uacute;mero</th><th>Estado</th></tr></thead>
                    <tbody id="waiterMesasBody"></tbody>
                </table>
            </div>
            <hr>
            <h5>Abrir servicio</h5>
            <div class="row g-2 mb-3">
                <div class="col-md-4">
                    <select id="waiterMesaSelect" class="form-select"></select>
                </div>
                <div class="col-md-4">
                    <button id="waiterOpenService" class="btn btn-primary">Abrir servicio</button>
                </div>
                <div class="col-md-4 d-flex align-items-end">
                    <button id="waiterRefreshMesas" class="btn btn-outline-secondary">Actualizar</button>
                </div>
            </div>
            <div id="waiterFlashMesas" class="mb-3"></div>
            <h5>Servicios activos</h5>
            <div id="waiterServiciosList"></div>
        `;

        this.renderMesasTable();
        this.container.querySelector('#waiterRefreshMesas').addEventListener('click', () => this.loadTab('mesas'));
        this.container.querySelector('#waiterOpenService').addEventListener('click', () => this.openService());
        this.renderServicios();
    }

    async loadMesas() {
        try {
            const data = await api.get('/mesas');
            this.mesas = data.data || [];
        } catch (err) {
            this.mesas = [];
            flash(err.message, 'danger');
        }
    }

    renderMesasTable() {
        const tbody = this.container.querySelector('#waiterMesasBody');
        const select = this.container.querySelector('#waiterMesaSelect');
        tbody.innerHTML = '';
        select.innerHTML = '<option value="">Seleccione una mesa</option>';

        this.mesas.forEach(m => {
            const tr = document.createElement('tr');
            const badge = `<span class="badge bg-${badgeColor(m.estado)}">${estadoLegible(m.estado)}</span>`;
            tr.innerHTML = `
                <td>Mesa ${m.numero}</td>
                <td>${badge}</td>
            `;
            tbody.appendChild(tr);

            if (m.estado === 'DISPONIBLE') {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = `Mesa ${m.numero}`;
                select.appendChild(opt);
            }
        });
    }

    async openService() {
        const select = this.container.querySelector('#waiterMesaSelect');
        const mesaId = select.value;
        if (!mesaId) {
            flash('Seleccione una mesa.', 'danger');
            return;
        }

        try {
            await api.post('/servicios', { mesa_id: parseInt(mesaId) });
            flash('Servicio abierto.', 'success');
            select.value = '';
            await this.loadTab('mesas');
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async loadServicios() {
        try {
            const data = await api.get('/servicios?estado=ACTIVO');
            this.servicios = data.data || [];
        } catch (err) {
            this.servicios = [];
            flash(err.message, 'danger');
        }
    }

    renderServicios() {
        const container = this.container.querySelector('#waiterServiciosList');
        if (this.servicios.length === 0) {
            container.innerHTML = '<p class="text-muted">No hay servicios activos.</p>';
            return;
        }

        let html = '<div class="table-responsive"><table class="table table-sm align-middle">';
        html += '<thead><tr><th>Servicio</th><th>Mesa</th><th>Estado</th><th>Total</th></tr></thead><tbody>';
        this.servicios.forEach(s => {
            html += `<tr>
                <td>#${s.id}</td>
                <td>Mesa ${s.mesa_id}</td>
                <td><span class="badge bg-${badgeColor(s.estado)}">${estadoLegible(s.estado)}</span></td>
                <td>${s.total}</td>
            </tr>`;
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    async renderPedidosTab(container) {
        await this.loadPedidosData();

        container.innerHTML = `
            <div class="row mb-3">
                <div class="col-md-4">
                    <h5>Nuevo pedido</h5>
                    <div class="row g-2">
                        <div class="col-md-5">
                            <select id="waiterPedidoServicio" class="form-select"></select>
                        </div>
                        <div class="col-md-4">
                            <select id="waiterPedidoProducto" class="form-select"></select>
                        </div>
                        <div class="col-md-2">
                            <input type="number" id="waiterPedidoCantidad" class="form-control" value="1" min="1">
                        </div>
                        <div class="col-md-1 d-flex align-items-end">
                            <button id="waiterPedidoAdd" class="btn btn-primary w-100">Agregar</button>
                        </div>
                    </div>
                    <div id="waiterPedidoItems" class="mt-2 p-2 border rounded bg-light"></div>
                    <button id="waiterPedidoCrear" class="btn btn-success mt-2">Crear pedido</button>
                </div>
                <div class="col-md-8">
                    <h5>Pendientes de autorizaci&oacute;n</h5>
                    <div id="waiterPendientes" class="mb-3"></div>
                    <h5>Pedidos en curso</h5>
                    <div id="waiterEnCurso" class="mb-3"></div>
                    <h5>Historial (entregados)</h5>
                    <div id="waiterHistorial"></div>
                </div>
            </div>
        `;

        const servicioSelect = this.container.querySelector('#waiterPedidoServicio');
        const productoSelect = this.container.querySelector('#waiterPedidoProducto');
        const cantidadInput = this.container.querySelector('#waiterPedidoCantidad');
        const addBtn = this.container.querySelector('#waiterPedidoAdd');
        const itemsContainer = this.container.querySelector('#waiterPedidoItems');
        const crearBtn = this.container.querySelector('#waiterPedidoCrear');

        this.servicios.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `Mesa ${s.mesa_id} (Servicio #${s.id})`;
            servicioSelect.appendChild(opt);
        });

        this.productos.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.name} - $${p.price}`;
            productoSelect.appendChild(opt);
        });

        this.pedidoItems = [];
        const renderItems = () => {
            itemsContainer.innerHTML = '';
            if (this.pedidoItems.length === 0) {
                itemsContainer.innerHTML = '<p class="text-muted small">Sin productos agregados.</p>';
                crearBtn.disabled = true;
                return;
            }
            let total = 0;
            this.pedidoItems.forEach((it, idx) => {
                total += parseFloat(it.precio) * it.cantidad;
                const div = document.createElement('div');
                div.className = 'd-flex justify-content-between align-items-center mb-1';
                div.innerHTML = `
                    <span>${it.productoName} x${it.cantidad}</span>
                    <button class="btn btn-sm btn-outline-danger" onclick="appWaiter.removePedidoItem(${idx})">&times;</button>
                `;
                itemsContainer.appendChild(div);
            });
            const totalDiv = document.createElement('div');
            totalDiv.className = 'text-end fw-bold';
            totalDiv.textContent = `Total: $${total.toFixed(2)}`;
            itemsContainer.appendChild(totalDiv);
            crearBtn.disabled = false;
        };

        addBtn.addEventListener('click', () => {
            const productoId = parseInt(productoSelect.value);
            const cantidad = parseInt(cantidadInput.value);
            const productoText = productoSelect.options[productoSelect.selectedIndex]?.text || '';
            const productoName = productoText.split(' - ')[0];
            const precio = parseFloat(productoText.split('$')[1] || 0);

            if (!productoId || !cantidad || cantidad <= 0) {
                flash('Seleccione un producto y cantidad v&aacute;lida.', 'danger');
                return;
            }

            this.pedidoItems.push({ producto_id: productoId, cantidad, productoName, precio });
            renderItems();
        });

        window.removePedidoItem = (idx) => {
            this.pedidoItems.splice(idx, 1);
            renderItems();
        };

        crearBtn.addEventListener('click', async () => {
            const servicioId = parseInt(servicioSelect.value);
            if (!servicioId || this.pedidoItems.length === 0) {
                flash('Seleccione un servicio y agregue al menos un producto.', 'danger');
                return;
            }

            const items = this.pedidoItems.map(it => ({ producto_id: it.producto_id, cantidad: it.cantidad }));
            try {
                await api.post(`/servicios/${servicioId}/pedidos`, { items });
                flash('Pedido creado exitosamente.', 'success');
                this.pedidoItems = [];
                renderItems();
                await this.loadPedidosData();
                this.renderPedidosGroups();
            } catch (err) {
                flash(err.message, 'danger');
            }
        });

        this.renderPedidosGroups();
    }

    async loadPedidosData() {
        try {
            const [pedidosRes, serviciosRes, productosRes] = await Promise.all([
                api.get('/pedidos'),
                api.get('/servicios'),
                api.get('/products')
            ]);
            this.pedidos = pedidosRes.data || [];
            this.servicios = serviciosRes.data || [];
            this.productos = (productosRes.data || []).filter(p => p.is_active !== false);
        } catch (err) {
            this.pedidos = [];
            this.servicios = [];
            this.productos = [];
            flash(err.message, 'danger');
        }
    }

    renderPedidosGroups() {
        const nombres = new Map(this.productos.map(p => [p.id, p.name]));
        const mesaPorServicio = new Map(this.servicios.map(s => [s.id, s.mesa_id]));

        const pendientes = this.pedidos.filter(p =>
            p.estado === 'PENDIENTE' && p.estado_preparacion === 'NO_ENVIADO' && p.autorizado_por_id === null
        );
        const enCurso = this.pedidos.filter(p => p.estado !== 'ENTREGADO' && !(p.estado === 'PENDIENTE' && p.estado_preparacion === 'NO_ENVIADO' && p.autorizado_por_id === null));
        const historial = this.pedidos.filter(p => p.estado === 'ENTREGADO');

        pendientes.sort((a, b) => b.id - a.id);
        enCurso.sort((a, b) => b.id - a.id);
        historial.sort((a, b) => b.id - a.id);

        const renderGroup = (containerId, pedidos, emptyMsg, allowActions = true) => {
            const container = document.getElementById(containerId);
            if (!container) return;
            if (pedidos.length === 0) {
                container.innerHTML = `<p class="text-muted">${emptyMsg}</p>`;
                return;
            }
            let html = '<table class="table table-sm align-middle">';
            html += '<thead><tr><th>ID</th><th>Mesa</th><th>Estado</th><th>Preparaci&oacute;n</th><th>Total</th><th>Acciones</th></tr></thead><tbody>';
            pedidos.forEach(p => {
                const mesaNumero = mesaPorServicio.get(p.servicio_id) || 'Desconocida';
                const actions = [];
                if (allowActions && p.estado === 'PENDIENTE' && p.estado_preparacion === 'NO_ENVIADO' && p.autorizado_por_id === null) {
                    actions.push(`<button class="btn btn-sm btn-primary" onclick="appWaiter.autorizar(${p.id})">Autorizar</button>`);
                }
                if (allowActions && p.estado === 'PENDIENTE' && p.estado_preparacion === 'NO_ENVIADO' && p.autorizado_por_id !== null) {
                    actions.push(`<button class="btn btn-sm btn-primary" onclick="appWaiter.enviarCocina(${p.id})">Enviar a cocina</button>`);
                }
                if (allowActions && p.estado === 'LISTO') {
                    actions.push(`<button class="btn btn-sm btn-success" onclick="appWaiter.entregar(${p.id})">Entregar</button>`);
                }
                actions.push(`<button class="btn btn-sm btn-outline-secondary" onclick="appWaiter.detalles(${p.id})">Detalles</button>`);
                html += `<tr>
                    <td>#${p.id}</td>
                    <td>Mesa ${mesaNumero}</td>
                    <td><span class="badge bg-${badgeColor(p.estado)}">${estadoLegible(p.estado)}</span></td>
                    <td>${estadoLegible(p.estado_preparacion)}</td>
                    <td>${p.total}</td>
                    <td>${actions.join(' ')}</td>
                </tr>`;
                html += `<tr><td colspan="6"><small>${p.items.map(i => `${i.cantidad} x ${nombres.get(i.producto_id) || 'Producto #' + i.producto_id}`).join(', ')}</small></td></tr>`;
            });
            html += '</tbody></table>';
            container.innerHTML = html;
        };

        renderGroup('waiterPendientes', pendientes, 'No hay pedidos pendientes de autorizaci&oacute;n.', true);
        renderGroup('waiterEnCurso', enCurso, 'No hay pedidos en curso.', true);
        renderGroup('waiterHistorial', historial, 'No hay pedidos entregados en el historial.', false);
    }

    async autorizar(pedidoId) {
        try {
            await api.post(`/pedidos/${pedidoId}/autorizar`, {});
            flash(`Pedido #${pedidoId} autorizado.`, 'success');
            await this.loadPedidosData();
            this.renderPedidosGroups();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async enviarCocina(pedidoId) {
        try {
            await api.post(`/pedidos/${pedidoId}/enviar-cocina`, {});
            flash(`Pedido #${pedidoId} enviado a cocina.`, 'success');
            await this.loadPedidosData();
            this.renderPedidosGroups();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async entregar(pedidoId) {
        try {
            await api.post(`/pedidos/${pedidoId}/entregar`, {});
            flash(`Pedido #${pedidoId} entregado.`, 'success');
            await this.loadPedidosData();
            this.renderPedidosGroups();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async detalles(pedidoId) {
        const p = this.pedidos.find(x => x.id === pedidoId);
        if (!p) return;
        const nombres = new Map(this.productos.map(x => [x.id, x.name]));
        const items = p.items.map(i => `${i.cantidad} x ${nombres.get(i.producto_id) || 'Producto #' + i.producto_id}`).join('<br>');
        alert(`Pedido #${p.id}\nEstado: ${estadoLegible(p.estado)}\nProductos:\n${items}`);
    }

    destroy() {}
}

window.appWaiter = null;