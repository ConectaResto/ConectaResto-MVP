document.addEventListener('DOMContentLoaded', function() {
    initNavToggle();
    initPostLinks();
    verifyPanelAccess();
});


/* --- Menú hamburguesa (móvil) --- */
function initNavToggle() {
    const toggle = document.getElementById('nav-toggle');
    const navList = document.querySelector('.nav-list');
    if (!toggle || !navList) return;

    toggle.addEventListener('click', function() {
        navList.classList.toggle('open');
    });

    // Cerrar menú al hacer clic en un enlace
    document.querySelectorAll('.nav-link').forEach(function(link) {
        link.addEventListener('click', function() {
            navList.classList.remove('open');
        });
    });
}


/* --- Enlaces con método POST (logout) vía fetch + CSRF --- */
function initPostLinks() {
    document.querySelectorAll('[method="post"], [data-method="post"]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            e.preventDefault();
            const url = el.getAttribute('href') || el.getAttribute('data-url');
            if (!url) return;

            const csrfToken = document.querySelector('meta[name="csrf-token"]');
            const token = csrfToken ? csrfToken.getAttribute('content') : '';

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRF-Token': token,
                },
            }).then(function(response) {
                if (response.ok) {
                    window.location.href = '/login';
                } else {
                    window.location.href = '/login';
                }
            }).catch(function() {
                window.location.href = '/login';
            });
        });
    });
}


/* --- Verificación de acceso a paneles --- */
async function verifyPanelAccess() {
    const isPanel = document.querySelector('.panel');
    const isLogin = document.getElementById('login-form');
    if (!isPanel && !isLogin) return;

    try {
        const response = await fetch('/auth/me');
        if (response.ok) {
            const data = await response.json();
            const userRol = data.data && data.data.rol;

            // Si estamos en login y ya hay sesión, redirigir al panel del rol
            if (isLogin) {
                const target = rolToPath(userRol);
                if (target) {
                    window.location.href = target;
                }
                return;
            }

            // Si estamos en un panel, verificar que el rol coincida
            const currentPath = window.location.pathname;
            const validPaths = rolPaths(userRol);
            const isValidPath = validPaths.some(function(p) {
                return currentPath === p || currentPath.startsWith(p + '/');
            });
            if (!isValidPath) {
                window.location.href = validPaths[0];
            }
        } else {
            // No autenticado
            if (isPanel) {
                window.location.href = '/login';
            }
        }
    } catch (err) {
        // Error de red, no hacer nada (la UI ya muestra el estado por defecto)
    }
}


function rolToPath(rol) {
    const map = {
        'ADMIN': '/admin',
        'WAITER': '/waiter',
        'KITCHEN': '/kitchen',
        'CASHIER': '/cashier',
    };
    return map[rol] || null;
}


function rolPaths(rol) {
    const lower = rol.toLowerCase();
    const base = '/' + lower;
    const panel = '/panel/' + lower;
    const paths = [base, panel];

    if (lower === 'waiter') {
        paths.push('/waiter/mesas', '/waiter/pedidos');
    } else if (lower === 'kitchen') {
        paths.push('/kitchen/pedidos');
    }

    return paths;
}
