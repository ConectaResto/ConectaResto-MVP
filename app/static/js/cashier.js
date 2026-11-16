document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    const token = csrfToken ? csrfToken.getAttribute('content') : '';

    let servicioSeleccionadoId = null;
    let operacionEnCurso = false;

    const serviciosGrid = document.getElementById('servicios-grid');
    const sinServicios = document.getElementById('sin-servicios');
    const detalleServicio = document.getElementById('detalle-servicio');
    const btnPagar = document.getElementById('btn-pagar-simulado');
    const btnCerrar = document.getElementById('btn-cerrar-servicio');
    const mensajeError = document.getElementById('mensaje-error');

    // One catalog request per page, shared by all service selections.
    const nombresProductos = fetch('/products', {
        headers: { 'X-CSRF-Token': token },
    }).then(async function(response) {
        if (!response.ok) return new Map();
        const data = await response.json();
        if (!Array.isArray(data.data)) return new Map();
        return new Map(data.data
            .filter(producto => producto.is_active !== false && producto.is_available !== false)
            .map(producto => [producto.id, producto.name]));
    }).catch(() => new Map());

    // Cargar servicios activos al iniciar
    cargarServiciosActivos();

    async function cargarServiciosActivos() {
        try {
            const response = await fetch('/servicios?estado=ACTIVO', {
                headers: {
                    'X-CSRF-Token': token,
                },
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                mostrarError('Error al cargar los servicios activos.');
                return;
            }

            const data = await response.json();
            const servicios = data.data || [];

            if (servicios.length === 0) {
                sinServicios.style.display = 'block';
                serviciosGrid.style.display = 'none';
                return;
            }

            sinServicios.style.display = 'none';
            serviciosGrid.style.display = 'grid';

            serviciosGrid.innerHTML = '';

            servicios.forEach(function(servicio) {
                const article = document.createElement('article');
                article.className = 'card tarjeta-servicio';
                article.setAttribute('data-servicio-id', servicio.id);

                const cardBody = document.createElement('div');
                cardBody.className = 'card-body';

                const h3 = document.createElement('h3');
                h3.className = 'card-title';
                h3.textContent = 'Servicio #' + servicio.id;

                const pMesa = document.createElement('p');
                pMesa.className = 'card-desc';
                pMesa.textContent = 'Mesa (ID) ' + servicio.mesa_id;

                const pEstado = document.createElement('p');
                pEstado.className = 'badge pending';
                pEstado.textContent = 'Estado: ' + servicio.estado;

                const total = document.createElement('p');
                total.className = 'cashier-card-total';
                total.textContent = '$' + servicio.total;

                const pago = document.createElement('p');
                pago.className = 'cashier-payment-status badge ' + (servicio.pago ? 'active' : 'pending');
                pago.textContent = servicio.pago ? 'Pago registrado' : 'Sin pago registrado';

                const btn = document.createElement('button');
                btn.className = 'btn btn-primary btn-seleccionar';
                btn.setAttribute('data-servicio-id', servicio.id);
                btn.textContent = 'Seleccionar';

                cardBody.appendChild(h3);
                cardBody.appendChild(pMesa);
                cardBody.appendChild(pEstado);
                cardBody.appendChild(total);
                cardBody.appendChild(pago);
                cardBody.appendChild(btn);
                article.appendChild(cardBody);
                serviciosGrid.appendChild(article);
            });

            // Agregar event listeners a los botones de seleccionar
            document.querySelectorAll('.btn-seleccionar').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    const servicioId = parseInt(this.getAttribute('data-servicio-id'));
                    seleccionarServicio(servicioId);
                });
            });
        } catch (err) {
            mostrarError('Error de conexión al cargar servicios.');
        }
    }

    async function seleccionarServicio(servicioId) {
        if (operacionEnCurso) return;
        servicioSeleccionadoId = servicioId;
        detalleServicio.style.display = 'none';
        btnPagar.disabled = true;
        btnCerrar.disabled = true;

        // Marcar tarjeta seleccionada
        document.querySelectorAll('.tarjeta-servicio').forEach(function(card) {
            card.classList.remove('seleccionada');
        });
        document.querySelector(`[data-servicio-id="${servicioId}"]`).classList.add('seleccionada');

        // Cargar detalles del servicio
        try {
            const response = await fetch(`/servicios/${servicioId}`, {
                headers: {
                    'X-CSRF-Token': token,
                },
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                if (servicioId !== servicioSeleccionadoId) return;
                mostrarError('Error al cargar los detalles del servicio.');
                return;
            }

            const data = await response.json();
            if (servicioId !== servicioSeleccionadoId) return;
            const servicio = data.data;

            const catalogo = await nombresProductos;
            if (servicioId !== servicioSeleccionadoId) return;

            // Mostrar detalle del servicio
            document.getElementById('detalle-servicio-id').textContent = servicio.id;
            document.getElementById('detalle-servicio-mesa').textContent = servicio.mesa_id;
            document.getElementById('detalle-servicio-estado').textContent = servicio.estado;
            const estadoPago = document.getElementById('detalle-pago-estado');
            estadoPago.textContent = servicio.pago ? 'Pago registrado' : 'Sin pago registrado';
            estadoPago.className = 'badge ' + (servicio.pago ? 'active' : 'pending');

            // Renderizar pedidos
            const pedidos = servicio.pedidos || [];
            const tablaBody = document.getElementById('tabla-pedidos-body');
            tablaBody.innerHTML = '';

            pedidos.forEach(function(pedido) {
                pedido.items.forEach(function(item) {
                    const fila = document.createElement('tr');
                    const valores = [
                        '#' + pedido.id, catalogo.get(item.producto_id) || 'Producto #' + item.producto_id,
                        item.cantidad, '$' + item.precio_unitario,
                        '$' + item.subtotal, pedido.estado,
                    ];
                    valores.forEach(function(valor) {
                        const celda = document.createElement('td');
                        celda.textContent = valor;
                        if (valor === pedido.estado) celda.className = 'cashier-order-state';
                        fila.appendChild(celda);
                    });
                    tablaBody.appendChild(fila);
                });
            });

            document.getElementById('detalle-total-pagar').textContent = '$' + servicio.total;

            const pedidosEntregados = pedidos.every(pedido => pedido.estado === 'ENTREGADO');
            btnPagar.disabled = Boolean(servicio.pago) || !pedidosEntregados || Number(servicio.total) <= 0;
            btnCerrar.disabled = pedidos.length > 0 && (!pedidosEntregados || !servicio.pago);
            btnPagar.textContent = servicio.pago ? 'Pago registrado' : 'Registrar pago simulado';
            detalleServicio.style.display = 'block';

            // Ocultar mensaje de error previo
            mensajeError.style.display = 'none';
        } catch (err) {
            if (servicioId !== servicioSeleccionadoId) return;
            mostrarError('Error de conexión al cargar detalles del servicio.');
        }
    }

    async function registrarPagoSimulado() {
        if (!servicioSeleccionadoId || operacionEnCurso || btnPagar.disabled) return;

        operacionEnCurso = true;
        btnPagar.disabled = true;
        btnPagar.textContent = 'Procesando...';

        try {
            const response = await fetch(`/servicios/${servicioSeleccionadoId}/pago-simulado`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token,
                },
                body: JSON.stringify({}),
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                const err = await response.json();
                mostrarError(err.error || 'Error al registrar el pago.');
                btnPagar.disabled = false;
                return;
            }

            btnPagar.disabled = true;
            btnCerrar.disabled = false;

            const estadoPago = document.getElementById('detalle-pago-estado');
            estadoPago.textContent = 'Pago registrado';
            estadoPago.className = 'badge active';
            const pagoTarjeta = document.querySelector(`[data-servicio-id="${servicioSeleccionadoId}"] .cashier-payment-status`);
            if (pagoTarjeta) {
                pagoTarjeta.textContent = 'Pago registrado';
                pagoTarjeta.className = 'cashier-payment-status badge active';
            }

            // Mostrar mensaje de éxito
            const mensajeDiv = document.createElement('div');
            mensajeDiv.className = 'flash exito';
            mensajeDiv.textContent = 'Pago registrado correctamente.';
            detalleServicio.insertBefore(mensajeDiv, detalleServicio.firstChild);

            setTimeout(function() {
                mensajeDiv.remove();
            }, 5000);
        } catch (err) {
            mostrarError('Error de conexión al registrar el pago.');
            btnPagar.disabled = false;
        } finally {
            operacionEnCurso = false;
            btnPagar.textContent = btnPagar.disabled ? 'Pago registrado' : 'Registrar pago simulado';
        }
    }

    async function cerrarServicio() {
        if (!servicioSeleccionadoId || operacionEnCurso || btnCerrar.disabled) return;

        operacionEnCurso = true;
        btnCerrar.disabled = true;
        btnCerrar.textContent = 'Cerrando...';

        try {
            const response = await fetch(`/servicios/${servicioSeleccionadoId}/cerrar`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token,
                },
                body: JSON.stringify({}),
            });

            if (response.status === 401 || response.status === 403) {
                window.location.href = '/login';
                return;
            }

            if (!response.ok) {
                const err = await response.json();
                mostrarError(err.error || 'Error al cerrar el servicio.');
                btnCerrar.disabled = false;
                btnCerrar.textContent = 'Cerrar servicio';
                return;
            }

            const data = await response.json();
            const servicio = data.data;

            // Mostrar confirmación de que la mesa quedó disponible
            const mensajeDiv = document.createElement('div');
            mensajeDiv.className = 'flash exito';
            mensajeDiv.textContent = `Servicio cerrado. Mesa ${servicio.mesa_id} disponible.`;
            detalleServicio.before(mensajeDiv);

            setTimeout(function() {
                mensajeDiv.remove();
            }, 5000);

            // Recargar lista de servicios activos
            cargarServiciosActivos();

            // Ocultar detalle y resetear estado
            detalleServicio.style.display = 'none';
            servicioSeleccionadoId = null;
            btnPagar.disabled = true;
            btnCerrar.disabled = true;
            btnPagar.textContent = 'Registrar pago simulado';
            btnCerrar.textContent = 'Cerrar servicio';
        } catch (err) {
            mostrarError('Error de conexión al cerrar el servicio.');
            btnCerrar.disabled = false;
        } finally {
            operacionEnCurso = false;
            btnCerrar.textContent = 'Cerrar servicio';
        }
    }

    function mostrarError(mensaje) {
        mensajeError.textContent = mensaje;
        mensajeError.style.display = 'block';
        setTimeout(function() {
            mensajeError.style.display = 'none';
        }, 5000);
    }

    btnPagar.addEventListener('click', registrarPagoSimulado);
    btnCerrar.addEventListener('click', cerrarServicio);
});
