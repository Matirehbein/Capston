// ../Public/js/dashboard.js

// NOTA: Asumo que 'colores.js' maneja el sidebar, así que este
// archivo se enfoca solo en los KPIs y modales.

// URL del backend
const API_BACKEND = "http://localhost:5000";

// --- Selectores ---
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Selector de Sucursal
const adminSucursalSelector = $("#admin-sucursal-selector");

// Card KPI Ventas (Corregidos para coincidir con tu HTML)
const kpiVentasCard = $("#kpi-ventas-hoy-card");
const kpiVentasMonto = $("#kpi-ventas"); // ID de tu HTML
const kpiVentasTrend = $("#kpi-ventas-trend"); // ID de tu HTML

// Modal 1 (Ventas Chart y Lista)
const salesChartModal = $("#sales-chart-modal");
const salesChartCloseBtn = $("#sales-chart-close-btn");
const salesComparisonFilter = $("#sales-comparison-filter");
const salesListTbody = $("#sales-list-tbody");
const salesChartCanvas = $("#salesChartCanvas");

// Modal 2 (Detalle Pedido)
const pedidosDetailModal = $("#pedidos-detail-modal");
const pedidosDetailCloseBtn = $("#pedidos-detail-close-btn");

// --- Selectores para Bajo Stock ---
const kpiBajoStockCard = $("#kpi-bajo-stock-card");
const kpiBajoStockMonto = $("#kpi-bajostock");
const kpiBajoStockNote = $("#kpi-bajostock-note");
const stockCategoriaModal = $("#stock-categoria-modal");
const stockCategoriaCloseBtn = $("#stock-categoria-close-btn");
const stockCategoriaTbody = $("#stock-categoria-tbody");
const stockProductoModal = $("#stock-producto-modal");
const stockProductoCloseBtn = $("#stock-producto-close-btn");
const stockProductoBackBtn = $("#stock-producto-back-btn");
const stockProductoTbody = $("#stock-producto-tbody");
const stockProductoTitulo = $("#stock-producto-titulo");

// --- ▼▼▼ NUEVOS Selectores para Nuevos Clientes ▼▼▼ ---
const kpiNuevosClientesCard = $("#kpi-nuevos-clientes-card");
const kpiNuevosClientesMonto = $("#kpi-clientes");
const kpiNuevosClientesTrend = $("#kpi-clientes-trend");

// Modal 1 (Lista Clientes)
const clientesListModal = $("#clientes-list-modal");
const clientesListCloseBtn = $("#clientes-list-close-btn");
const clientesPeriodoFilter = $("#clientes-periodo-filter");
const clientesListTbody = $("#clientes-list-tbody");

// Modal 2 (Detalle Cliente)
const clientesDetailModal = $("#clientes-detail-modal");
const clientesDetailCloseBtn = $("#clientes-detail-close-btn");
const clientesDetailBackBtn = $("#clientes-detail-back-btn");
const clientePedidosTbody = $("#cliente-pedidos-tbody");

// --- ▼▼▼ Selectores para Pedidos Pendientes ▼▼▼ ---
const kpiPedidosPendientesCard = $("#kpi-pedidos-pendientes-card");
const kpiPedidosPendientesMonto = $("#kpi-pendientes");              
const kpiPedidosPendientesTrend = $("#kpi-pendientes-sub");          

// --- ▲▲▲ FIN NUEVOS Selectores ▲▲▲ ---

// Variable global para el gráfico
let salesChart = null;

// --- Funciones de Ayuda ---
function formatCLP(value) {
    const numberValue = Number(value) || 0;
    return numberValue.toLocaleString("es-CL", {
        style: "currency",
        currency: "CLP",
        maximumFractionDigits: 0
    });
}

function formatFecha(isoString, includeTime = true) {
    if (!isoString) return "N/A";
    try {
        const date = new Date(isoString);
        const options = {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
        };
        if (includeTime) {
            options.hour = '2-digit';
            options.minute = '2-digit';
            options.hour12 = true; // Para formato "p. m." o "a. m."
        }
        return date.toLocaleString('es-CL', options);
    } catch (e) {
        return isoString;
    }
}

// --- Lógica de Carga de Datos ---

/**
 * Carga el selector de sucursales
 */
async function cargarSucursales() {
    if (!adminSucursalSelector) return;
    try {
        // Esta ruta ya existe en tu app.py (la usa Reportes)
        const response = await fetch(`${API_BACKEND}/api/sucursales_con_coords`); 
        if (!response.ok) throw new Error("No se pudieron cargar las sucursales");
        
        const sucursales = await response.json();
        
        sucursales.forEach(sucursal => {
            const option = document.createElement("option");
            option.value = sucursal.id_sucursal;
            option.textContent = sucursal.nombre_sucursal;
            adminSucursalSelector.appendChild(option);
        });

    } catch (error) {
        console.error("Error cargando sucursales:", error);
    }
}

/**
 * Carga TODOS los KPIs del dashboard
 */
function loadAllKPIs(sucursalId = 'all') {
    loadKPIVentasHoy(sucursalId);
    loadKPIBajoStock(sucursalId);
    loadKPINuevosClientes(sucursalId); 
    loadKPIPedidosPendientes(sucursalId); 
    // ... aquí irían las llamadas a loadKPIPedidosPendientes(sucursalId)
}


/**
 * Carga el KPI principal de "Ventas hoy"
 */
async function loadKPIVentasHoy(sucursalId = 'all') {
    if (!kpiVentasMonto || !kpiVentasTrend) return;
    kpiVentasMonto.textContent = "...";
    kpiVentasTrend.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/kpi_ventas_hoy?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) window.location.href = '/src/login.html';
            throw new Error("Error al cargar KPI de ventas.");
        }
        const data = await response.json();
        kpiVentasMonto.textContent = formatCLP(data.ventas_hoy);
        
        // --- CORRECCIÓN: Convertir a número explícitamente ---
        const trend = Number(data.porcentaje_vs_ayer); 
        
        kpiVentasTrend.className = "kpi-trend";
        if (trend > 0) {
            kpiVentasTrend.textContent = `▲ ${trend.toFixed(0)}% vs. ayer`;
            kpiVentasTrend.classList.add("positive");
        } else if (trend < 0) {
            kpiVentasTrend.textContent = `▼ ${Math.abs(trend).toFixed(0)}% vs. ayer`;
            kpiVentasTrend.classList.add("negative");
        } else {
            kpiVentasTrend.textContent = "0% vs. ayer";
            kpiVentasTrend.classList.add("neutral");
        }
    } catch (error) {
        console.error("Error en loadKPIVentasHoy:", error);
        kpiVentasMonto.textContent = "Error";
        kpiVentasTrend.textContent = "N/A";
    }
}

/**
 * Carga el KPI principal de "Productos con bajo stock".
 */
async function loadKPIBajoStock(sucursalId = 'all') {
    if (!kpiBajoStockMonto || !kpiBajoStockNote) return;
    kpiBajoStockMonto.textContent = "...";
    kpiBajoStockNote.textContent = "... unidades";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/kpi_bajo_stock?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar KPI de bajo stock.");
        const data = await response.json();
        kpiBajoStockMonto.textContent = data.conteo_bajo_stock || 0;
        kpiBajoStockNote.textContent = `${data.conteo_bajo_stock || 0} productos <= 20 unidades`;
    } catch (error) {
        console.error("Error en loadKPIBajoStock:", error);
        kpiBajoStockMonto.textContent = "Error";
    }
}

// --- ▼▼▼ NUEVA FUNCION: Cargar KPI de Nuevos Clientes ▼▼▼ ---
/**
 * Carga el KPI principal de "Nuevos clientes HOY".
 */
async function loadKPINuevosClientes(sucursalId = 'all') {
    if (!kpiNuevosClientesMonto || !kpiNuevosClientesTrend) return;

    kpiNuevosClientesMonto.textContent = "...";
    kpiNuevosClientesTrend.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/kpi_nuevos_clientes?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar KPI de clientes.");
        
        const data = await response.json();
        
        kpiNuevosClientesMonto.textContent = data.clientes_hoy || 0;
        
        // --- CORRECCIÓN: Convertir a número explícitamente ---
        const trend = Number(data.porcentaje_vs_ayer);
        
        kpiNuevosClientesTrend.className = "kpi-trend"; // Reset
        if (trend > 0) {
            kpiNuevosClientesTrend.textContent = `▲ ${trend.toFixed(0)}% vs. ayer`;
            kpiNuevosClientesTrend.classList.add("positive");
        } else if (trend < 0) {
            kpiNuevosClientesTrend.textContent = `▼ ${Math.abs(trend).toFixed(0)}% vs. ayer`;
            kpiNuevosClientesTrend.classList.add("negative");
        } else {
            kpiNuevosClientesTrend.textContent = "0% vs. ayer";
            kpiNuevosClientesTrend.classList.add("neutral");
        }

    } catch (error) {
        console.error("Error en loadKPINuevosClientes:", error);
        kpiNuevosClientesMonto.textContent = "Error";
        kpiNuevosClientesTrend.textContent = "N/A";
    }
}
// --- ▲▲▲ FIN NUEVA FUNCION ▲▲▲ ---


/**
 * Carga los datos para el gráfico de comparación en el Modal 1.
 */
async function loadVentasChart(sucursalId = 'all', periodo = 'ayer') {
    if (!salesChartCanvas) return;

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/chart_ventas?sucursal_id=${sucursalId}&periodo=${periodo}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar datos del gráfico.");
        const data = await response.json();
        if (salesChart) salesChart.destroy();

        const ctx = salesChartCanvas.getContext('2d');
        salesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels, 
                datasets: [{
                    label: 'Ventas',
                    data: data.data, 
                    backgroundColor: ['rgba(13, 110, 253, 0.7)', 'rgba(108, 117, 125, 0.7)'],
                    borderColor: ['rgba(13, 110, 253, 1)', 'rgba(108, 117, 125, 1)'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (ctx) => `Ventas: ${formatCLP(ctx.parsed.y)}` } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (val) => (val >= 1000000 ? `$${val / 1000000}M` : (val >= 1000 ? `$${val / 1000}k` : formatCLP(val))) }
                    }
                }
            }
        });
    } catch (error) {
        console.error("Error en loadVentasChart:", error);
    }
}

/**
 * Carga la lista de ventas de hoy en el Modal 1.
 */
async function loadVentasHoyList(sucursalId = 'all') {
    if (!salesListTbody) return;
    salesListTbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Cargando...</td></tr>';
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/lista_ventas_hoy?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar la lista de ventas.");
        const ventas = await response.json();
        if (ventas.length === 0) {
            salesListTbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No se encontraron ventas hoy.</td></tr>';
            return;
        }
        let html = '';
        ventas.forEach(venta => {
            const fechaStr = formatFecha(venta.creado_en, true);
            const hora = fechaStr.includes(',') ? fechaStr.split(', ')[1] : fechaStr;
            html += `
                <tr>
                    <td>#${venta.id_pedido}</td>
                    <td>${venta.cliente_nombre || 'N/A'}</td>
                    <td>${venta.productos_preview || 'Sin detalle'}...</td>
                    <td>${hora || 'N/A'}</td>
                    <td><a href="#" class="sale-detail-link" data-id-pedido="${venta.id_pedido}">Ver detalle</a></td>
                </tr>`;
        });
        salesListTbody.innerHTML = html;
    } catch (error) {
        console.error("Error en loadVentasHoyList:", error);
        salesListTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Error al cargar la lista.</td></tr>`;
    }
}

// --- Lógica para Modal 2 (Detalle Pedido) ---

function openPedidosDetailModal(id_pedido) {
    if (pedidosDetailModal) {
        pedidosDetailModal.classList.add('visible');
        loadPedidoDetailData(id_pedido);
    }
}

function closePedidosDetailModal() {
    if (pedidosDetailModal) {
        pedidosDetailModal.classList.remove('visible');
        $all('#pedidos-detail-modal span[id^="detalle-"]').forEach(span => span.textContent = '...');
        const tbody = $('#detalle-items-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="text-center">...</td></tr>';
    }
}

async function loadPedidoDetailData(id_pedido) {
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/detalle_pedido/${id_pedido}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor al buscar detalle.");
        const data = await response.json();
        const pedido = data.pedido;
        const items = data.items;
        if (!pedido) throw new Error("El pedido no se encontró o no tiene datos.");

        const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''} ${pedido.apellido_materno || ''}`.trim();
        const direccionCompleta = `${pedido.calle || ''} ${pedido.numero_calle || ''}`.trim();
        
        $('#detalle-cliente-nombre').textContent = nombreCompleto;
        $('#detalle-cliente-email').textContent = pedido.email_usuario || 'N/A';
        $('#detalle-cliente-telefono').textContent = pedido.telefono || 'N/A';
        $('#detalle-cliente-direccion').textContent = direccionCompleta || 'No especificada';
        $('#detalle-cliente-comuna').textContent = pedido.comuna || 'N/A';
        $('#detalle-cliente-ciudad').textContent = pedido.ciudad || 'N/A';
        $('#detalle-cliente-region').textContent = pedido.region || 'N/A';
        
        $('#detalle-pedido-id').textContent = pedido.id_pedido;
        $('#detalle-pedido-id-2').textContent = pedido.id_pedido;
        $('#detalle-pedido-sucursal').textContent = pedido.nombre_sucursal || 'No especificada';
        $('#detalle-pedido-fecha').textContent = formatFecha(pedido.creado_en, true);
        $('#detalle-pedido-total').textContent = formatCLP(pedido.total);
        $('#detalle-pedido-metodo').textContent = pedido.metodo_pago || 'N/A';

        let estadoPago = 'Pendiente';
        if (pedido.estado_pedido === 'rechazado') estadoPago = 'Rechazado';
        else if (pedido.metodo_pago) estadoPago = 'Aprobado';
        $('#detalle-pedido-estado-pago').textContent = estadoPago;

        let estadoPedido = pedido.estado_pedido;
        if (estadoPedido === 'pagado') estadoPedido = 'Por despachar';
        $('#detalle-pedido-estado-pedido').textContent = estadoPedido;

        const itemsTbody = $('#detalle-items-tbody');
        let itemsHtml = '';
        if (items && items.length > 0) {
            items.forEach(item => {
                itemsHtml += `
                    <tr>
                        <td><img src="${item.imagen_url || '../Public/img/placeholder.png'}" alt="${item.nombre_producto || ''}" class="item-foto"></td>
                        <td>${item.nombre_producto || 'Producto no encontrado'}</td>
                        <td>${item.sku_producto || 'N/A'}</td>
                        <td>${item.talla || 'Única'}</td>
                        <td>${item.color || 'N/A'}</td>
                        <td>${item.cantidad}</td>
                        <td>${formatCLP(item.precio_unitario)}</td>
                    </tr>`;
            });
        } else {
            itemsHtml = '<tr><td colspan="7" class="text-center">No se encontraron items.</td></tr>';
        }
        itemsTbody.innerHTML = itemsHtml;

    } catch (error) {
        console.error(`Error en loadPedidoDetailData: ${error}`);
        $('#detalle-cliente-nombre').textContent = `Error al cargar: ${error.message}`;
    }
}


// --- Lógica para Modales de Bajo Stock ---

function openStockCategoriaModal() {
    stockCategoriaModal?.classList.add('visible');
    const sucursalId = adminSucursalSelector?.value || 'all';
    loadStockCategoriaList(sucursalId);
}

function closeStockCategoriaModal() {
    stockCategoriaModal?.classList.remove('visible');
}

function openStockProductoModal(categoria) {
    stockProductoModal?.classList.add('visible');
    stockCategoriaModal?.classList.remove('visible'); 
    const sucursalId = adminSucursalSelector?.value || 'all';
    loadStockProductoList(categoria, sucursalId);
}

function closeStockProductoModal(volver = false) {
    stockProductoModal?.classList.remove('visible');
    if (volver) {
        stockCategoriaModal?.classList.add('visible');
    }
}

async function loadStockCategoriaList(sucursalId = 'all') {
    if (!stockCategoriaTbody) return;
    stockCategoriaTbody.innerHTML = '<tr><td colspan="2" style="text-align: center;">Cargando...</td></tr>';

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/stock_por_categoria?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar categorías.");
        
        const categorias = await response.json();

        if (categorias.length === 0) {
            stockCategoriaTbody.innerHTML = '<tr><td colspan="2" style="text-align: center;">No hay productos con bajo stock.</td></tr>';
            return;
        }

        let html = '';
        categorias.forEach(cat => {
            if (cat.conteo_bajo_stock > 0) { 
                html += `
                    <tr>
                        <td>
                            <a href="#" class="stock-categoria-link" data-categoria="${cat.categoria}">
                                ${cat.categoria}
                            </a>
                        </td>
                        <td>
                            <span class="fw-bold text-danger">${cat.conteo_bajo_stock}</span> / ${cat.total_productos} productos
                        </td>
                    </tr>
                `;
            }
        });

        if (html === '') {
            html = '<tr><td colspan="2" style="text-align: center;">¡Felicidades! No hay productos con bajo stock.</td></tr>';
        }
        stockCategoriaTbody.innerHTML = html;

    } catch (error) {
        console.error("Error en loadStockCategoriaList:", error);
        stockCategoriaTbody.innerHTML = `<tr><td colspan="2" style="text-align: center; color: red;">${error.message}</td></tr>`;
    }
}

async function loadStockProductoList(categoria, sucursalId = 'all') {
    if (!stockProductoTbody || !stockProductoTitulo) return;
    stockProductoTitulo.textContent = `Productos en ${categoria}`;
    stockProductoTbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Cargando...</td></tr>';

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/productos_por_categoria?categoria=${encodeURIComponent(categoria)}&sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar productos.");
        
        const productos = await response.json();

        if (productos.length === 0) {
            stockProductoTbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">No se encontraron productos.</td></tr>';
            return;
        }

        let html = '';
        productos.forEach(item => {
            const stock = item.total_stock;
            let stockClass = '';

            if (stock <= 20) {
                stockClass = 'text-danger fw-bold';
            } else if (stock <= 30) {
                stockClass = 'text-warning fw-bold';
            } else {
                stockClass = 'text-success';
            }

            html += `
                <tr>
                    <td><img src="${item.imagen_url || '../Public/img/placeholder.png'}" alt="${item.nombre_producto}" class="item-foto"></td>
                    <td class="${stockClass}">${item.nombre_producto}</td>
                    <td class="${stockClass}">${stock} unidades</td>
                </tr>
            `;
        });
        stockProductoTbody.innerHTML = html;

    } catch (error) {
        console.error("Error en loadStockProductoList:", error);
        stockProductoTbody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: red;">${error.message}</td></tr>`;
    }
}


// --- Inicialización y Listeners ---
document.addEventListener("DOMContentLoaded", () => {
    
    // Carga inicial
    cargarSucursales();
    loadAllKPIs('all'); // Carga todos los KPIs para "Todas las sucursales"

    // --- Listener para el FILTRO DE SUCURSAL ---
    adminSucursalSelector?.addEventListener('change', () => {
        const sucursalIdSeleccionada = adminSucursalSelector.value;
        // Recargar todos los KPIs con la nueva sucursal
        loadAllKPIs(sucursalIdSeleccionada);
    });

    // --- Listeners para "Ventas Hoy" ---
    kpiVentasCard?.addEventListener('click', () => {
        const sucursalId = adminSucursalSelector?.value || 'all';
        salesChartModal?.classList.add('visible');
        loadVentasChart(sucursalId, 'ayer'); // Carga el gráfico por defecto
        loadVentasHoyList(sucursalId); // Carga la lista
    });

    salesChartCloseBtn?.addEventListener('click', () => {
        salesChartModal?.classList.remove('visible');
    });
    salesChartModal?.addEventListener('click', (e) => {
        if (e.target === salesChartModal) salesChartModal.classList.remove('visible');
    });

    salesComparisonFilter?.addEventListener('change', (e) => {
        const sucursalId = adminSucursalSelector?.value || 'all';
        loadVentasChart(sucursalId, e.target.value);
    });

    salesListTbody?.addEventListener('click', (e) => {
        const link = e.target.closest('.sale-detail-link');
        if (link) {
            e.preventDefault();
            const pedidoId = link.dataset.idPedido;
            if (pedidoId) {
                openPedidosDetailModal(pedidoId);
            }
        }
    });

    pedidosDetailCloseBtn?.addEventListener('click', () => {
        closePedidosDetailModal();
    });
    pedidosDetailModal?.addEventListener('click', (e) => {
        if (e.target === pedidosDetailModal) closePedidosDetailModal();
    });

    // --- Listeners para "Bajo Stock" ---
    kpiBajoStockCard?.addEventListener('click', () => {
        openStockCategoriaModal();
    });

    stockCategoriaCloseBtn?.addEventListener('click', () => {
        closeStockCategoriaModal();
    });
    stockCategoriaModal?.addEventListener('click', (e) => {
        if (e.target === stockCategoriaModal) closeStockCategoriaModal();
    });

    stockCategoriaTbody?.addEventListener('click', (e) => {
        const link = e.target.closest('.stock-categoria-link');
        if (link) {
            e.preventDefault();
            const categoria = link.dataset.categoria;
            if (categoria) {
                openStockProductoModal(categoria);
            }
        }
    });

    stockProductoCloseBtn?.addEventListener('click', () => {
        stockProductoModal?.classList.remove('visible'); 
    });
    stockProductoModal?.addEventListener('click', (e) => {
        if (e.target === stockProductoModal) stockProductoModal.classList.remove('visible');
    });

    stockProductoBackBtn?.addEventListener('click', () => {
        closeStockProductoModal(true); // Cierra Modal 2 y reabre Modal 1
    });

    // --- ▼▼▼ NUEVOS Listeners para Nuevos Clientes ▼▼▼ ---

    // Listener para abrir Modal 1 (Lista Clientes)
    kpiNuevosClientesCard?.addEventListener('click', () => {
        openClientesListModal();
    });

    // Listener para cerrar Modal 1 (Lista Clientes)
    clientesListCloseBtn?.addEventListener('click', () => closeClientesListModal());
    clientesListModal?.addEventListener('click', (e) => {
        if (e.target === clientesListModal) closeClientesListModal();
    });

    // Listener para el filtro de PERÍODO de clientes
    clientesPeriodoFilter?.addEventListener('change', () => {
        const sucursalId = adminSucursalSelector?.value || 'all';
        const periodo = clientesPeriodoFilter.value;
        loadClientesList(sucursalId, periodo);
    });

    // Listener para clic en la lista de clientes (abrir Modal 2)
    clientesListTbody?.addEventListener('click', (e) => {
        const link = e.target.closest('.cliente-detail-link');
        if (link) {
            e.preventDefault();
            const clienteId = link.dataset.idCliente;
            if (clienteId) openClientesDetailModal(clienteId);
        }
    });

    // Listener para cerrar Modal 2 (Detalle Cliente)
    clientesDetailCloseBtn?.addEventListener('click', () => closeClientesDetailModal(false));
    clientesDetailModal?.addEventListener('click', (e) => {
        if (e.target === clientesDetailModal) closeClientesDetailModal(false);
    });

    // Listener para el botón "Volver"
    clientesDetailBackBtn?.addEventListener('click', () => closeClientesDetailModal(true));

    // Listener para clic en la lista de pedidos (abrir Modal 3 - Detalle Pedido)
    clientePedidosTbody?.addEventListener('click', (e) => {
        const link = e.target.closest('.sale-detail-link'); // Reutilizamos la clase
        if (link) {
            e.preventDefault();
            const pedidoId = link.dataset.idPedido;
            if (pedidoId) openPedidosDetailModal(pedidoId);
        }
    });

    // --- ▲▲▲ FIN NUEVOS Listeners ▲▲▲ ---
});

async function loadKPIPedidosPendientes(sucursalId = 'all') {
    const kpiNum = $("#kpi-pendientes");
    const kpiSub = $("#kpi-pendientes-sub");

    if (!kpiNum || !kpiSub) return;

    kpiNum.textContent = "...";
    kpiSub.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/kpi_pedidos_pendientes?sucursal_id=${sucursalId}`, { credentials: "include" });

        if (!response.ok) throw new Error("Error cargando KPI pedidos");

        const data = await response.json();

        // ✔ USAR LA KEY CORRECTA
        const value = data.pendientes ?? 0;

        kpiNum.textContent = value;
        kpiSub.textContent = `${value} pedidos esperando acción`;

        kpiSub.className = "kpi-trend warn";

    } catch (e) {
        console.error("Error KPI pendientes:", e);
        kpiNum.textContent = "Error";
        kpiSub.textContent = "N/A";
    }
}

async function loadPedidosPendientesList(sucursalId = 'all') {
    const tbody = $("#pendientes-list-tbody");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="5">Cargando...</td></tr>`;

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/lista_pedidos_pendientes?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });

        if (!response.ok) throw new Error("Error cargando lista pendientes");

        const pedidos = await response.json();

        if (pedidos.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5">No hay pedidos pendientes.</td></tr>`;
            return;
        }

        let html = "";
        pedidos.forEach(p => {
            html += `
                <tr>
                    <td>#${p.id_pedido}</td>
                    <td>${p.cliente || "N/A"}</td>
                    <td>${formatFecha(p.creado_en, true)}</td>
                    <td>${p.estado_pedido}</td>
                    <td><a href="#" class="sale-detail-link" data-id-pedido="${p.id_pedido}">Ver detalle</a></td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

    } catch (e) {
        console.error("Error lista pendientes:", e);
        tbody.innerHTML = `<tr><td colspan="5" style="color:red;">Error al cargar</td></tr>`;
    }
}
// --- Abrir Modal de Pedidos Pendientes ---
kpiPedidosPendientesCard?.addEventListener("click", () => {
    const sucursalId = adminSucursalSelector?.value || "all";
    $("#pendientes-list-modal").classList.add("visible");
    loadPedidosPendientesList(sucursalId);
});

// --- Cerrar Modal ---
$("#pendientes-list-close-btn")?.addEventListener("click", () => {
    $("#pendientes-list-modal").classList.remove("visible");
});

// Cerrar al hacer click fuera
$("#pendientes-list-modal")?.addEventListener("click", (e) => {
    if (e.target === $("#pendientes-list-modal")) {
        $("#pendientes-list-modal").classList.remove("visible");
    }
});

// Click en "Ver detalle"
$("#pendientes-list-tbody")?.addEventListener("click", (e) => {
    const link = e.target.closest(".sale-detail-link");
    if (link) {
        e.preventDefault();
        openPedidosDetailModal(link.dataset.idPedido);
    }
});

