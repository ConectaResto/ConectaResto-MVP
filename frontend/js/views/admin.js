class AdminView {
    constructor(container) {
        this.container = container;
        this.currentSection = 'mesas';
    }

    async init() {
        window.appAdmin = this;
        this.container.innerHTML = `
            <div class="view-card">
                <div class="view-card-header">Panel Administrador</div>
                <div class="view-card-body">
                    <ul class="nav nav-tabs mb-3" id="adminTabs">
                        <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#adminMesas">Mesas y QR</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#adminCategorias">Categor&iacute;as</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#adminProductos">Productos</button></li>
                        <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#adminUsuarios">Usuarios</button></li>
                    </ul>
                    <div class="tab-content" id="adminTabContent">
                        <div class="tab-pane fade show active" id="adminMesas"></div>
                        <div class="tab-pane fade" id="adminCategorias"></div>
                        <div class="tab-pane fade" id="adminProductos"></div>
                        <div class="tab-pane fade" id="adminUsuarios"></div>
                    </div>
                </div>
            </div>
        `;

        this.container.querySelectorAll('#adminTabs button').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.target.dataset.bsTarget.replace('#', '');
                this.currentSection = target;
                this.loadSection(target);
            });
        });

        this.loadSection('mesas');
    }

    async loadSection(section) {
        const container = this.container.querySelector(`#admin${section.charAt(0).toUpperCase() + section.slice(1)}`);
        container.innerHTML = '<div class="text-center py-4"><div class="spinner-border" role="status"></div></div>';

        try {
            if (section === 'mesas') await this.loadMesas(container);
            if (section === 'categorias') await this.loadCategorias(container);
            if (section === 'productos') await this.loadProductos(container);
            if (section === 'usuarios') await this.loadUsuarios(container);
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async loadMesas(container) {
        const data = await api.get('/admin/mesas');
        const mesas = data.data || [];

        container.innerHTML = `
            <h5>Mesas y QR</h5>
            <div class="row g-3 mb-3">
                <div class="col-md-4">
                    <input type="number" id="adminMesaNumero" class="form-control" placeholder="N&uacute;mero de mesa" min="1">
                </div>
                <div class="col-md-4">
                    <select id="adminMesaEstado" class="form-select">
                        <option value="DISPONIBLE">Disponible</option>
                        <option value="OCUPADA">Ocupada</option>
                        <option value="CERRADA">Cerrada</option>
                    </select>
                </div>
                <div class="col-md-4 d-flex align-items-end">
                    <button id="adminMesaCreate" class="btn btn-primary w-100">Crear mesa</button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover align-middle">
                    <thead><tr><th>N&uacute;mero</th><th>Estado</th><th>QR</th><th>Acciones</th></tr></thead>
                    <tbody>
                        ${mesas.map(m => `
                            <tr>
                                <td>Mesa ${m.numero}</td>
                                <td><span class="badge bg-${badgeColor(m.estado)}">${estadoLegible(m.estado)}</span></td>
                                <td><button class="btn btn-sm btn-outline-primary" onclick="appAdmin.verQr(${m.id})">Ver QR</button></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="appAdmin.editMesa(${m.id}, '${m.numero}', '${m.estado}')">Editar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        this.container.querySelector('#adminMesaCreate').addEventListener('click', () => this.crearMesa());
    }

    async crearMesa() {
        const numeroInput = this.container.querySelector('#adminMesaNumero');
        const estadoSelect = this.container.querySelector('#adminMesaEstado');
        const numero = parseInt(numeroInput.value);
        const estado = estadoSelect.value;

        if (!numero) {
            flash('Ingrese un n&uacute;mero v&aacute;lido.', 'danger');
            return;
        }

        try {
            await api.post('/admin/mesas', { numero, estado });
            flash('Mesa creada.', 'success');
            numeroInput.value = '';
            this.loadSection('mesas');
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async editMesa(id, numero, estado) {
        const n = prompt('N&uacute;mero de mesa:', numero);
        if (n === null) return;
        const e = prompt('Estado (DISPONIBLE/OCUPADA/CERRADA):', estado);
        if (e === null) return;

        try {
            await api.patch(`/admin/mesas/${id}`, { numero: parseInt(n), estado: e });
            flash('Mesa actualizada.', 'success');
            this.loadSection('mesas');
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async verQr(mesaId) {
        try {
            const blob = await fetch(`/admin/mesas/${mesaId}/qr.svg`, { credentials: 'same-origin' }).then(r => r.blob());
            const url = URL.createObjectURL(blob);
            const img = document.createElement('img');
            img.src = url;
            img.style.maxWidth = '200px';
            img.style.border = '1px solid #dee2e6';
            img.style.borderRadius = '0.25rem';
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-dark text-white">
                            <h5 class="modal-title">QR Mesa</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center"></div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                        </div>
                    </div>
                </div>
            `;
            modal.querySelector('.modal-body').appendChild(img);
            document.body.appendChild(modal);
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            modal.addEventListener('hidden.bs.modal', () => {
                URL.revokeObjectURL(url);
                document.body.removeChild(modal);
            });
        } catch (err) {
            flash(err.message, 'danger');
        }
    }

    async loadCategorias(container) {
        const data = await api.get('/categories?include_inactive=true');
        const cats = data.data || [];

        container.innerHTML = `
            <h5>Categor&iacute;as</h5>
            <div class="row g-3 mb-3">
                <div class="col-md-6">
                    <input type="text" id="adminCatName" class="form-control" placeholder="Nombre" maxlength="100">
                </div>
                <div class="col-md-4">
                    <input type="text" id="adminCatDesc" class="form-control" placeholder="Descripci&oacute;n" maxlength="500">
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button id="adminCatCreate" class="btn btn-primary w-100">Crear</button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover align-middle">
                    <thead><tr><th>Nombre</th><th>Descripci&oacute;n</th><th>Acciones</th></tr></thead>
                    <tbody>
                        ${cats.map(c => `
                            <tr>
                                <td>${c.name}</td>
                                <td>${c.description || '-'}</td>
                                <td>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="appAdmin.editCategoria(${c.id}, '${c.name}', '${c.description || ''}')">Editar</button>
                                    <button class="btn btn-sm btn-outline-danger" onclick="appAdmin.deleteCategoria(${c.id})">Desactivar</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        this.container.querySelector('#adminCatCreate').addEventListener('click', () => this.crearCategoria());
    }

    async crearCategoria() {
        const name = this.container.querySelector('#adminCatName').value.trim();
        const desc = this.container.querySelector('#adminCatDesc').value.trim();
        if (!name) { flash('Nombre requerido.', 'danger'); return; }
        try {
            await api.post('/categories', { name, description: desc });
            flash('Categor&iacute;a creada.', 'success');
            this.container.querySelector('#adminCatName').value = '';
            this.container.querySelector('#adminCatDesc').value = '';
            this.loadSection('categorias');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async editCategoria(id, name, desc) {
        const n = prompt('Nombre:', name);
        if (n === null) return;
        const d = prompt('Descripci&oacute;n:', desc);
        if (d === null) return;
        try {
            await api.patch(`/categories/${id}`, { name: n, description: d });
            flash('Categor&iacute;a actualizada.', 'success');
            this.loadSection('categorias');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async deleteCategoria(id) {
        if (!confirm('¿Desactivar esta categor&iacute;a?')) return;
        try {
            await api.del(`/categories/${id}`);
            flash('Categor&iacute;a desactivada.', 'success');
            this.loadSection('categorias');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async loadProductos(container) {
        const [prodData, catData] = await Promise.all([
            api.get('/admin/products?include_inactive=true'),
            api.get('/categories?include_inactive=true')
        ]);
        const productos = prodData.data || [];
        const categorias = catData.data || [];

        container.innerHTML = `
            <h5>Productos</h5>
            <div class="row g-3 mb-3">
                <div class="col-md-3">
                    <input type="text" id="adminProdName" class="form-control" placeholder="Nombre" maxlength="100">
                </div>
                <div class="col-md-3">
                    <input type="text" id="adminProdDesc" class="form-control" placeholder="Descripci&oacute;n" maxlength="500">
                </div>
                <div class="col-md-2">
                    <input type="number" id="adminProdPrice" class="form-control" placeholder="Precio" min="0" step="0.01">
                </div>
                <div class="col-md-2">
                    <select id="adminProdCat" class="form-select">
                        <option value="">Categor&iacute;a</select>
                        ${categorias.filter(c => c.is_active).map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                    </select>
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button id="adminProdCreate" class="btn btn-primary w-100">Crear</button>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover align-middle">
                    <thead><tr><th>Nombre</th><th>Categor&iacute;a</th><th>Precio</th><th>Disponible</th><th>Activo</th><th>Acciones</th></tr></thead>
                    <tbody>
                        ${productos.map(p => {
                            const cat = categorias.find(c => c.id === p.categoria_id);
                            return `
                                <tr>
                                    <td>${p.name}</td>
                                    <td>${cat ? cat.name : '#' + p.categoria_id}</td>
                                    <td>${p.price}</td>
                                    <td><span class="badge bg-${p.is_available ? 'success' : 'secondary'}">${p.is_available ? 'S&iacute;' : 'No'}</span></td>
                                    <td><span class="badge bg-${p.is_active ? 'success' : 'danger'}">${p.is_active ? 'S&iacute;' : 'No'}</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-secondary" onclick="appAdmin.editProducto(${p.id}, '${p.name}', '${p.description || ''}', ${p.price}, ${p.categoria_id}, ${p.is_available})">Editar</button>
                                        ${p.is_active ? `<button class="btn btn-sm btn-outline-danger" onclick="appAdmin.deleteProducto(${p.id})">Desactivar</button>` : `<button class="btn btn-sm btn-outline-success" onclick="appAdmin.reactivarProducto(${p.id})">Reactivar</button>`}
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        this.container.querySelector('#adminProdCreate').addEventListener('click', () => this.crearProducto());
    }

    async crearProducto() {
        const data = {
            name: this.container.querySelector('#adminProdName').value.trim(),
            description: this.container.querySelector('#adminProdDesc').value.trim(),
            price: this.container.querySelector('#adminProdPrice').value,
            categoria_id: parseInt(this.container.querySelector('#adminProdCat').value),
            is_available: true
        };
        if (!data.name || !data.categoria_id) { flash('Nombre y categor&iacute;a requeridos.', 'danger'); return; }
        try {
            await api.post('/products', data);
            flash('Producto creado.', 'success');
            this.loadSection('productos');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async editProducto(id, name, desc, price, catId, isAvailable) {
        const n = prompt('Nombre:', name);
        if (n === null) return;
        const d = prompt('Descripci&oacute;n:', desc);
        if (d === null) return;
        const p = prompt('Precio:', price);
        if (p === null) return;
        try {
            await api.patch(`/products/${id}`, { name: n, description: d, price: p });
            flash('Producto actualizado.', 'success');
            this.loadSection('productos');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async deleteProducto(id) {
        if (!confirm('¿Desactivar este producto?')) return;
        try {
            await api.del(`/products/${id}`);
            flash('Producto desactivado.', 'success');
            this.loadSection('productos');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async reactivarProducto(id) {
        try {
            await api.patch(`/products/${id}`, { is_active: true });
            flash('Producto reactivado.', 'success');
            this.loadSection('productos');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async loadUsuarios(container) {
        const data = await api.get('/users');
        const users = data.data.users || data.data || [];

        container.innerHTML = `
            <h5>Usuarios</h5>
            <div class="row g-3 mb-3">
                <div class="col-md-3">
                    <input type="text" id="adminUserUsername" class="form-control" placeholder="Usuario" maxlength="80">
                </div>
                <div class="col-md-3">
                    <input type="email" id="adminUserEmail" class="form-control" placeholder="Correo electr&oacute;nico" maxlength="120">
                </div>
                <div class="col-md-3">
                    <select id="adminUserRol" class="form-select">
                        <option value="WAITER">Mesero</option>
                        <option value="KITCHEN">Cocina</option>
                        <option value="CASHIER">Cajero</option>
                        <option value="ADMIN">Administrador</option>
                    </select>
                </div>
                <div class="col-md-3">
                    <input type="password" id="adminUserPassword" class="form-control" placeholder="Contrase&ntilde;a">
                </div>
            </div>
            <div class="d-grid mb-3">
                <button id="adminUserCreate" class="btn btn-primary">Crear usuario</button>
            </div>
            <div class="table-responsive">
                <table class="table table-striped table-hover align-middle">
                    <thead><tr><th>Usuario</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Acciones</th></tr></thead>
                    <tbody>
                        ${users.map(u => `
                            <tr>
                                <td>${u.username}</td>
                                <td>${u.email}</td>
                                <td>${u.rol}</td>
                                <td><span class="badge bg-${u.is_active ? 'success' : 'danger'}">${u.is_active ? 'Activo' : 'Inactivo'}</span></td>
                                <td>
                                    <button class="btn btn-sm btn-outline-secondary" onclick="appAdmin.editUsuario(${u.id}, '${u.username}', '${u.email}', '${u.rol}', ${u.is_active})">Editar</button>
                                    ${u.is_active ? `<button class="btn btn-sm btn-outline-danger" onclick="appAdmin.deleteUsuario(${u.id})">Desactivar</button>` : `<button class="btn btn-sm btn-outline-success" onclick="appAdmin.reactivarUsuario(${u.id})">Reactivar</button>`}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;

        this.container.querySelector('#adminUserCreate').addEventListener('click', () => this.crearUsuario());
    }

    async crearUsuario() {
        const data = {
            username: this.container.querySelector('#adminUserUsername').value.trim(),
            email: this.container.querySelector('#adminUserEmail').value.trim(),
            rol: this.container.querySelector('#adminUserRol').value,
            password: this.container.querySelector('#adminUserPassword').value
        };
        if (!data.username || !data.email || !data.password) { flash('Todos los campos son requeridos.', 'danger'); return; }
        try {
            await api.post('/users', data);
            flash('Usuario creado.', 'success');
            this.container.querySelector('#adminUserUsername').value = '';
            this.container.querySelector('#adminUserEmail').value = '';
            this.container.querySelector('#adminUserPassword').value = '';
            this.loadSection('usuarios');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async editUsuario(id, username, email, rol, isActive) {
        const u = prompt('Usuario:', username);
        if (u === null) return;
        const e = prompt('Correo:', email);
        if (e === null) return;
        const r = prompt('Rol (ADMIN/WAITER/KITCHEN/CASHIER):', rol);
        if (r === null) return;
        try {
            await api.patch(`/users/${id}`, { username: u, email: e, rol: r });
            flash('Usuario actualizado.', 'success');
            this.loadSection('usuarios');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async deleteUsuario(id) {
        if (!confirm('¿Desactivar este usuario?')) return;
        try {
            await api.del(`/users/${id}`);
            flash('Usuario desactivado.', 'success');
            this.loadSection('usuarios');
        } catch (err) { flash(err.message, 'danger'); }
    }

    async reactivarUsuario(id) {
        try {
            await api.patch(`/users/${id}`, { is_active: true });
            flash('Usuario reactivado.', 'success');
            this.loadSection('usuarios');
        } catch (err) { flash(err.message, 'danger'); }
    }

    destroy() {}
}

window.appAdmin = null;