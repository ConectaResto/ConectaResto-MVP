class KitchenView {
    constructor(container) {
        this.container = container;
        this.pedidos = [];
        this.productos = [];
    }

    async init() {
        window.appKitchen = this;
        this.container.innerHTML = `
            <div class="view-card">
                <div class="view-card-header">Panel Cocina</div>
                <div class="view-card-body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5>Pedidos activos</h5>
                        <button id="kitchenRefresh" class="btn btn-outline-primary btn-sm">Actualizar</button>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm align-middle" id="kitchenTable">
                            <thead><tr>
                                <th>Pedido</th><th>Servicio</th><th>Productos</th><th>Estado</th><th>Preparaci&oacute;n</th><th>Total</th><th>Acciones</th>
                            </tr></thead>
                            <tbody id="kitchenBody"></tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        this.container.querySelector('#kitchenRefresh').addEventListener('click', () => this.load());
        await this.load();
    }

    async load() {
        this.container.querySelector('#kitchenBody').innerHTML = '<tr><td colspan="7" class="text-center"><div class="spinner-border" role="status"></div></td></tr>';
        try {
            const data = await api.get('/pedidos');
            this.pedidos = data.data || [];
            const prodData = await api.get('/products');
            this.productos = (prodData.data || []).filter(p => p.is_active !== false);
            const nombres = new Map(this.productos.map(p => [p.id, p.name]));

            const activos = this.pedidos.filter(p => ['RECIBIDO', 'EN_COCINA'].includes(p.estado_preparacion));
            const tbody = this.container.querySelector('#kitchenBody');
            tbody.innerHTML = '';

            activos.forEach(p => {
                const itemsHtml = p.items.map(i => {
                    const prod = nombres.get(i.producto_id) || `Producto #${i.producto_id}`;
                    return `${i.cantidad} x ${prod}`;
                }).join('<br>');

                const prepBadge = `<span class="badge bg-${badgeColor(p.estado_preparacion)}">${estadoLegible(p.estado_preparacion)}</span>`;
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>#${p.id}</td>
                    <td>#${p.servicio_id}</td>
                    <td>${itemsHtml}</td>
                    <td><span class="badge bg-secondary">${estadoLegible(p.estado)}</span></td>
                    <td>${prepBadge}</td>
                    <td>${p.total}</td>
                    <td>
                        ${p.estado_preparacion === 'RECIBIDO' ?
                            `<button class="btn btn-sm btn-primary" onclick="appKitchen.cambiarPreparacion(${p.id}, 'EN_COCINA')">En cocina</button>` : ''
                        }
                        ${p.estado_preparacion === 'EN_COCINA' ?
                            `<button class="btn btn-sm btn-success" onclick="appKitchen.cambiarPreparacion(${p.id}, 'LISTO_PARA_SERVIR')">Listo para servir</button>` : ''
                        }
                    </td>
                `;
                tbody.appendChild(row);
            });

            if (activos.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No hay pedidos activos.</td></tr>';
            }
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async cambiarPreparacion(pedidoId, nuevoEstado) {
        try {
            await api.patch(`/pedidos/${pedidoId}/preparacion`, { estado: nuevoEstado });
            flash(`Pedido #${pedidoId} ${estadoLegible(nuevoEstado)}.`, 'success');
            await this.load();
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    destroy() {}
}

window.appKitchen = null;