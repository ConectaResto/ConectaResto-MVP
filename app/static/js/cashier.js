document.addEventListener('DOMContentLoaded', function() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]');
    const token = csrfToken ? csrfToken.getAttribute('content') : '';

    let servicioSeleccionadoId = null;
    let pagoRegistrado = false;

    const serviciosGrid = document.getElementById('servicios-grid');
    const sinServicios = document.getElementById('sin-servicios');
    const detalleServicio = document.getElementById('detalle-servicio');
    const btnPagar = document.getElementById('btn-pagar-simulado');
    const btnCerrar = document.getElementById('btn-cerrar-servicio');
    const mensajeError = document.getElementById('mensaje-error');

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
                pMesa.textContent = 'Mesa ' + servicio.mesa_id;

                const pEstado = document.createElement('p');
                pEstado.className = 'card-desc';
                pEstado.style.fontSize = '0.85rem';
                pEstado.style.color = '#666';
                pEstado.textContent = 'Estado: ' + servicio.estado;

                const btn = document.createElement('button');
                btn.className = 'btn btn-primary btn-seleccionar';
                btn.setAttribute('data-servicio-id', servicio.id);
                btn.textContent = 'Seleccionar';

                cardBody.appendChild(h3);
                cardBody.appendChild(pMesa);
                cardBody.appendChild(pEstado);
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
        servicioSeleccionadoId = servicioId;
        pagoRegistrado = false;

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
                mostrarError('Error al cargar los detalles del servicio.');
                return;
            }

            const data = await response.json();
            const servicio = data.data;

            // Mostrar detalle del servicio
            document.getElementById('detalle-servicio-id').textContent = servicio.id;
            document.getElementById('detalle-servicio-mesa').textContent = servicio.mesa_id;
            document.getElementById('detalle-servicio-estado').textContent = servicio.estado;

            // Renderizar pedidos
            const pedidos = servicio.pedidos || [];
            const tablaBody = document.getElementById('tabla-pedidos-body');
            tablaBody.innerHTML = '';

            let total = 0;
            pedidos.forEach(function(pedido) {
                pedido.items.forEach(function(item) {
                    const subtotal = item.precio_unitario * item.cantidad;
                    total += subtotal;

                    const fila = document.createElement('tr');

            const tdProducto = document.createElement('td');
            tdProducto.textContent = item.producto_id;
            fila.appendChild(tdProducto);

            const tdCantidad = document.createElement('td');
            tdCantidad.textContent = item.cantidad;
            fila.appendChild(tdCantidad);

            const tdPrecio = document.createElement('td');
            tdPrecio.textContent = '$' + item.precio_unitario.toFixed(2);
            fila.appendChild(tdPrecio);

            const tdSubtotal = document.createElement('td');
            tdSubtotal.textContent = '$' + subtotal.toFixed(2);
            fila.appendChild(tdSubtotal);

            const tdEstado = document.createElement('td');
            tdEstado.textContent = pedido.estado_preparacion;
            fila.appendChild(tdEstado);

            tablaBody.appendChild(fila);
                });
            });

            document.getElementById('detalle-total-pagar').textContent = `$${total.toFixed(2)}`;

            // Mostrar detalle y actualizar botones
            detalleServicio.style.display = 'block';
            btnPagar.disabled = false;
            btnCerrar.disabled = true; // No se puede cerrar sin pago
            pagoRegistrado = false;

            // Ocultar mensaje de error previo
            mensajeError.style.display = 'none';
        } catch (err) {
            mostrarError('Error de conexión al cargar detalles del servicio.');
        }
    }

    async function registrarPagoSimulado() {
        if (!servicioSeleccionadoId || pagoRegistrado) return;

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

            const data = await response.json();
            const servicio = data.data;

            pagoRegistrado = true;
            btnPagar.disabled = true;
            btnCerrar.disabled = false;

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
        }
    }

    async function cerrarServicio() {
        if (!servicioSeleccionadoId || !pagoRegistrado) return;

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
            detalleServicio.insertBefore(mensajeDiv, detalleServicio.firstChild);

            setTimeout(function() {
                mensajeDiv.remove();
            }, 5000);

            // Recargar lista de servicios activos
            cargarServiciosActivos();

            // Ocultar detalle y resetear estado
            detalleServicio.style.display = 'none';
            servicioSeleccionadoId = null;
            pagoRegistrado = false;
            btnPagar.disabled = true;
            btnCerrar.disabled = true;
            btnPagar.textContent = 'Registrar pago simulado';
            btnCerrar.textContent = 'Cerrar servicio';
        } catch (err) {
            mostrarError('Error de conexión al cerrar el servicio.');
            btnCerrar.disabled = false;
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