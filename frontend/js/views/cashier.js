class CashierView {
    constructor(container) {
        this.container = container;
        this.servicios = [];
        this.selectedServiceId = null;
    }

    async init() {
        window.appCashier = this;
        this.container.innerHTML = `
            <div class="view-card">
                <div class="view-card-header">Panel Caja</div>
                <div class="view-card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5>Servicios activos</h5>
                        <button id="cashierRefresh" class="btn btn-outline-primary btn-sm">Actualizar</button>
                    </div>
                    <div class="row g-3">
                        <div class="col-lg-8" id="cashierServices"></div>
                        <div class="col-lg-4" id="cashierDetail"></div>
                    </div>
                </div>
            </div>
        `;

        this.container.querySelector('#cashierRefresh').addEventListener('click', () => this.load());
        await this.load();
    }

    async load() {
        try {
            const data = await api.get('/servicios?estado=ACTIVO');
            this.servicios = data.data || [];
            this.renderServices();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    renderServices() {
        const container = this.container.querySelector('#cashierServices');
        if (this.servicios.length === 0) {
            container.innerHTML = '<p class="text-muted">No hay servicios activos pendientes de cobro.</p>';
            return;
        }

        let html = '<div class="list-group list-group-flush">';
        this.servicios.forEach(s => {
            const pagoEstado = s.pago ? 'Pago registrado' : 'Sin pago';
            const badge = s.pago ? 'bg-success' : 'bg-warning text-dark';
            html += `
                <div class="list-group-item list-group-item-action d-flex justify-content-between align-items-center cursor-pointer" onclick="appCashier.selectService(${s.id})">
                    <div>
                        <div class="fw-bold">Servicio #${s.id} - Mesa ${s.mesa_id}</div>
                        <div class="small text-muted">Estado: ${estadoLegible(s.estado)}</div>
                    </div>
                    <div>
                        <div class="fw-bold">${s.total}</div>
                        <div class="badge ${badge}">${pagoEstado}</div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    async selectService(serviceId) {
        this.selectedServiceId = serviceId;
        try {
            const data = await api.get(`/servicios/${serviceId}`);
            const servicio = data.data;
            this.renderDetail(servicio);
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    renderDetail(servicio) {
        const container = this.container.querySelector('#cashierDetail');
        const pedidosHtml = servicio.pedidos.map(p => {
            const itemsHtml = p.items.map(i => `${i.cantidad} x ${i.producto_id} - ${i.precio_unitario}`).join(', ');
            return `
                <tr>
                    <td>#${p.id}</td>
                    <td>${itemsHtml}</td>
                    <td>${p.total}</td>
                    <td><span class="badge bg-${badgeColor(p.estado)}">${estadoLegible(p.estado)}</span></td>
                </tr>
            `;
        }).join('');

        const allEntregados = servicio.pedidos.length > 0 && servicio.pedidos.every(p => p.estado === 'ENTREGADO');
        const tienePago = !!servicio.pago;

        container.innerHTML = `
            <div class="card">
                <div class="card-header bg-dark text-white">
                    <h6 class="mb-0">Servicio #${servicio.id} - Mesa ${servicio.mesa_id}</h6>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <strong>Estado:</strong> <span class="badge bg-${badgeColor(servicio.estado)}">${estadoLegible(servicio.estado)}</span>
                    </div>
                    <table class="table table-sm mb-3">
                        <thead><tr><th>Pedido</th><th>Productos</th><th>Total</th><th>Estado</th></tr></thead>
                        <tbody>${pedidosHtml}</tbody>
                    </table>
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <span><strong>Total del servicio:</strong></span>
                        <span class="fw-lg fs-5">${servicio.total}</span>
                    </div>
                    <div class="mb-3">
                        <strong>Pago:</strong>
                        <span class="badge ${tienePago ? 'bg-success' : 'bg-warning text-dark'} ms-2">
                            ${tienePago ? 'Registrado' : 'Sin pago'}
                        </span>
                    </div>
                    <div class="d-grid gap-2">
                        ${!tienePago && allEntregados && parseFloat(servicio.total) > 0 ?
                            `<button id="cashierPay" class="btn btn-success">Registrar pago simulado</button>` :
                            `<button id="cashierPay" class="btn btn-success" disabled>Registrar pago simulado</button>`
                        }
                        ${tienePago && allEntregados ?
                            `<button id="cashierClose" class="btn btn-danger">Cerrar servicio</button>` :
                            `<button id="cashierClose" class="btn btn-danger" disabled>Cerrar servicio</button>`
                        }
                    </div>
                </div>
            </div>
        `;

        this.container.querySelector('#cashierPay').addEventListener('click', () => this.registrarPago(servicio.id));
        this.container.querySelector('#cashierClose').addEventListener('click', () => this.cerrarServicio(servicio.id));
    }

    async registrarPago(serviceId) {
        try {
            await api.post(`/servicios/${serviceId}/pago-simulado`, {});
            flash('Pago registrado correctamente.', 'success');
            this.selectService(serviceId);
            this.load();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async cerrarServicio(serviceId) {
        if (!confirm('¿Est&aacute; seguro de cerrar este servicio?')) return;
        try {
            const data = await api.post(`/servicios/${serviceId}/cerrar`, {});
            flash(`Servicio cerrado. Mesa ${data.data.mesa_id} disponible.`, 'success');
            this.selectedServiceId = null;
            this.container.querySelector('#cashierDetail').innerHTML = '';
            this.load();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    destroy() {}
}

window.appCashier = null;