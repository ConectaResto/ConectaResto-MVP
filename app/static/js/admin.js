/* Administración sobre las APIs existentes. Los datos se insertan como texto. */
document.addEventListener('DOMContentLoaded', async function () {
    'use strict';
    const panel = document.getElementById('admin-panel');
    if (!panel) return;

    const csrf = document.querySelector('meta[name="csrf-token"]').content;
    const resources = {
        mesas: { path: '/admin/mesas', singular: 'mesa', fields: ['numero', 'estado'], rows: [] },
        categorias: { path: '/categories', listPath: '/categories?include_inactive=true', singular: 'categoría', fields: ['name', 'description'], rows: [] },
        productos: { path: '/products', listPath: '/admin/products?include_inactive=true', singular: 'producto', fields: ['name', 'description', 'price', 'categoria_id', 'is_available'], rows: [] },
        usuarios: { path: '/users', singular: 'usuario', fields: ['username', 'email', 'rol'], rows: [] },
    };
    let currentUserId = null;
    let qrUrl = null;

    function feedback(section, message, error = false) {
        const target = section.querySelector('[data-feedback]');
        target.textContent = message;
        target.className = error ? 'flash error' : 'flash';
        target.setAttribute('role', error ? 'alert' : 'status');
        target.hidden = false;
    }

    async function request(url, options = {}) {
        const headers = { Accept: 'application/json' };
        if (options.method) {
            headers['X-CSRF-Token'] = csrf;
            headers['Content-Type'] = 'application/json';
        }
        const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
        const payload = await response.json().catch(() => null);
        if (response.status === 401) throw new Error('La sesión venció. Inicia sesión nuevamente.');
        if (response.status === 403) throw new Error('No tienes permisos para esta operación.');
        if (!response.ok || !payload || payload.success !== true) {
            throw new Error(payload?.error || 'No se pudo completar la operación. Actualiza e intenta nuevamente.');
        }
        return payload;
    }

    function setBusy(section, busy) {
        section.dataset.busy = String(busy);
        section.querySelector('fieldset').disabled = busy;
        section.querySelectorAll('button').forEach(button => {
            button.disabled = busy || button.dataset.locked === 'true';
        });
    }

    function resetForm(section, resource) {
        const form = section.querySelector('form');
        form.reset();
        delete form.dataset.recordId;
        section.querySelector('[data-form-title]').textContent = 'Crear ' + resource.singular;
        if (form.elements.password) form.elements.password.required = true;
    }

    function edit(section, resource, record) {
        const form = section.querySelector('form');
        resetForm(section, resource);
        form.dataset.recordId = String(record.id);
        for (const field of resource.fields) {
            const input = form.elements.namedItem(field);
            if (input.type === 'checkbox') input.checked = Boolean(record[field]);
            else input.value = record[field] ?? '';
        }
        if (form.elements.password) {
            form.elements.password.value = '';
            form.elements.password.required = false;
        }
        section.querySelector('[data-form-title]').textContent = 'Editar ' + resource.singular + ' #' + record.id;
        form.querySelector('input').focus();
    }

    function closeQr() {
        document.getElementById('mesa-qr').hidden = true;
        document.getElementById('mesa-qr-image').removeAttribute('src');
        if (qrUrl) URL.revokeObjectURL(qrUrl);
        qrUrl = null;
    }

    async function showQr(record) {
        closeQr();
        const response = await fetch('/admin/mesas/' + record.id + '/qr.svg', {
            credentials: 'same-origin', headers: { Accept: 'image/svg+xml' },
        });
        if (!response.ok) {
            const payload = await response.json().catch(() => null);
            throw new Error(payload?.error || 'No se pudo cargar el QR. Comprueba tu sesión.');
        }
        if (!response.headers.get('Content-Type')?.includes('image/svg+xml')) {
            throw new Error('El servidor no devolvió una imagen QR válida.');
        }
        qrUrl = URL.createObjectURL(await response.blob());
        const image = document.getElementById('mesa-qr-image');
        image.src = qrUrl;
        image.alt = 'Código QR de la mesa ' + record.numero;
        document.getElementById('mesa-qr-title').textContent = 'QR de la mesa ' + record.numero;
        document.getElementById('mesa-qr').hidden = false;
    }

    function render(section, name) {
        const resource = resources[name];
        const body = section.querySelector('[data-rows]');
        body.replaceChildren();
        for (const record of resource.rows) {
            const row = document.createElement('tr');
            let values;
            if (name === 'mesas') values = [record.id, record.numero, record.estado];
            if (name === 'categorias') values = [record.id, record.name, record.description || '—', record.is_active ? 'Activo' : 'Inactivo'];
            if (name === 'productos') {
                const category = resources.categorias.rows.find(item => item.id === record.categoria_id);
                values = [record.id, record.name, record.price, category?.name || '#' + record.categoria_id,
                    record.is_available ? 'Disponible' : 'No disponible', record.is_active ? 'Activo' : 'Inactivo'];
            }
            if (name === 'usuarios') values = [record.id, record.username, record.email, record.rol, record.is_active ? 'Activo' : 'Inactivo'];
            for (const value of values) {
                const cell = document.createElement('td');
                cell.textContent = String(value);
                row.appendChild(cell);
            }
            const actions = document.createElement('td');
            const choices = ['editar'];
            if (name === 'mesas') choices.push('qr');
            if (['categorias', 'productos', 'usuarios'].includes(name)) {
                if (!record.is_active) choices.push('reactivar');
                else choices.push('desactivar');
            }
            for (const action of choices) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn';
                button.textContent = { editar: 'Editar', qr: 'Ver QR', desactivar: 'Desactivar', reactivar: 'Reactivar' }[action];
                button.dataset.action = action;
                button.dataset.recordId = String(record.id);
                button.setAttribute('aria-label', button.textContent + ' ' + resource.singular + ' #' + record.id);
                if (name === 'usuarios' && action === 'desactivar' && record.id === currentUserId) {
                    button.disabled = true;
                    button.dataset.locked = 'true';
                    button.title = 'No puedes desactivar tu propia cuenta';
                }
                actions.appendChild(button);
            }
            row.appendChild(actions);
            body.appendChild(row);
        }
        const categoryHelp = name === 'categorias'
            ? 'Para desactivar una categoría, primero desactiva o reasigna sus productos activos. Marcar un producto como no disponible no lo desactiva. ' : '';
        section.querySelector('[data-list-status]').textContent = categoryHelp + (resource.rows.length ? '' : 'No hay registros para mostrar.');
    }

    async function loadList(section, name) {
        const resource = resources[name];
        section.querySelector('[data-list-status]').textContent = 'Cargando…';
        const payload = await request(resource.listPath || resource.path);
        resource.rows = name === 'usuarios' ? payload.data.users : payload.data;
        render(section, name);
        if (name === 'categorias') {
            const select = document.getElementById('producto-categoria');
            const selected = select.value;
            select.replaceChildren(new Option('Selecciona una categoría', ''));
            for (const category of resource.rows.filter(item => item.is_active)) select.add(new Option(category.name, String(category.id)));
            select.value = selected;
        }
    }

    function payloadFor(form, name) {
        const field = key => form.elements.namedItem(key);
        if (name === 'mesas') return { numero: Number(field('numero').value), estado: field('estado').value };
        if (name === 'categorias') return { name: field('name').value.trim(), description: field('description').value.trim() };
        if (name === 'productos') return {
            name: field('name').value.trim(), description: field('description').value.trim(),
            price: field('price').value, categoria_id: Number(field('categoria_id').value),
            is_available: field('is_available').checked,
        };
        const data = { username: field('username').value.trim(), email: field('email').value.trim(), rol: field('rol').value };
        if (field('password').value) data.password = field('password').value;
        field('password').value = '';
        return data;
    }

    try {
        currentUserId = (await request('/auth/me')).data.id;
    } catch (error) {
        panel.querySelectorAll('[data-admin-section]').forEach(section => {
            feedback(section, error.message, true);
            setBusy(section, true);
        });
        return;
    }

    for (const section of panel.querySelectorAll('[data-admin-section]')) {
        const name = section.dataset.adminSection;
        const resource = resources[name];
        const form = section.querySelector('form');
        section.querySelector('[data-cancel]').addEventListener('click', () => resetForm(section, resource));
        section.querySelector('[data-refresh]').addEventListener('click', async () => {
            if (section.dataset.busy === 'true') return;
            setBusy(section, true);
            try {
                if (name === 'mesas') closeQr();
                if (name === 'productos') await loadList(document.getElementById('admin-categorias'), 'categorias');
                await loadList(section, name);
                feedback(section, 'Lista actualizada.');
            } catch (error) {
                feedback(section, error.message, true);
                section.querySelector('[data-list-status]').textContent = 'No se pudo actualizar la lista.';
            } finally {
                setBusy(section, false);
            }
        });
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (section.dataset.busy === 'true' || !form.reportValidity()) return;
            const recordId = form.dataset.recordId;
            const data = payloadFor(form, name);
            setBusy(section, true);
            try {
                await request(resource.path + (recordId ? '/' + recordId : ''), {
                    method: recordId ? 'PATCH' : 'POST', body: JSON.stringify(data),
                });
                if (name === 'usuarios' && Number(recordId) === currentUserId) {
                    const me = await request('/auth/me');
                    if (me.data.rol !== 'ADMIN') {
                        window.location.assign('/');
                        return;
                    }
                }
                resetForm(section, resource);
                feedback(section, 'Cambios guardados.');
                try {
                    await loadList(section, name);
                } catch (error) {
                    feedback(section, 'Cambios guardados. No se pudo actualizar la lista: ' + error.message, true);
                }
            } catch (error) {
                feedback(section, error.message, true);
            } finally {
                setBusy(section, false);
            }
        });
        section.querySelector('[data-rows]').addEventListener('click', async event => {
            const button = event.target.closest('button[data-action]');
            if (!button || section.dataset.busy === 'true') return;
            const record = resource.rows.find(item => item.id === Number(button.dataset.recordId));
            if (!record) return;
            if (button.dataset.action === 'editar') {
                edit(section, resource, record);
                return;
            }
            if (button.dataset.action === 'desactivar' && !window.confirm('¿Desactivar ' + resource.singular + ' #' + record.id + '?')) return;
            setBusy(section, true);
            try {
                if (button.dataset.action === 'qr') await showQr(record);
                else {
                    const reactivating = button.dataset.action === 'reactivar';
                    await request(resource.path + '/' + record.id, reactivating
                        ? { method: 'PATCH', body: JSON.stringify({ is_active: true }) }
                        : { method: 'DELETE' });
                    resetForm(section, resource);
                    await loadList(section, name);
                    feedback(section, reactivating ? 'Registro reactivado.' : 'Registro desactivado.');
                }
            } catch (error) {
                feedback(section, error.message, true);
            } finally {
                setBusy(section, false);
            }
        });
        setBusy(section, true);
        try {
            await loadList(section, name);
        } catch (error) {
            feedback(section, error.message, true);
            section.querySelector('[data-list-status]').textContent = 'No se pudo cargar la lista.';
        } finally {
            setBusy(section, false);
        }
    }
    document.getElementById('cerrar-qr').addEventListener('click', closeQr);
    window.addEventListener('pagehide', closeQr);
});
