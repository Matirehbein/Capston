// ../Public/js/reportes_admin.js

// URL de tu backend
const API_BACKEND = "http://localhost:5000";

// --- Variables Globales para el Gráfico ---
let salesChart = null; // Instancia global del gráfico
let currentChartData = null; // Para guardar los datos actuales
let currentChartType = 'bar'; // Tipo de gráfico por defecto

// --- Funciones de Ayuda ---
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

/**
 * Formatea un número como moneda Chilena (CLP).
 */
function formatCLP(value) {
    const numberValue = Number(value) || 0;
    try {
        return numberValue.toLocaleString("es-CL", {
            style: "currency",
            currency: "CLP",
            maximumFractionDigits: 0
        });
    } catch (e) {
        return `$${Math.round(numberValue)}`;
    }
}

/**
 * Formatea una fecha ISO (o de DB) a un formato legible.
 */
function formatFecha(isoString) {
    if (!isoString) return "N/A";
    try {
        const date = new Date(isoString);
        // es-CL: dd-mm-aaaa, hh:mm
        return date.toLocaleString('es-CL', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return isoString; // Devuelve el string original si falla
    }
}

/**
 * Carga todas las sucursales desde la API
 * y las añade al selector del panel de admin.
 */
async function cargarSucursales() {
    const selector = $("#admin-sucursal-selector");
    if (!selector) return;

    try {
        const response = await fetch(`${API_BACKEND}/api/sucursales_con_coords`);
        if (!response.ok) throw new Error("No se pudieron cargar las sucursales");

        const sucursales = await response.json();

        sucursales.forEach(sucursal => {
            const option = document.createElement("option");
            option.value = sucursal.id_sucursal;
            option.textContent = sucursal.nombre_sucursal;
            selector.appendChild(option);
        });

    } catch (error) {
        console.error("Error cargando sucursales:", error);
        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Error al cargar";
        option.disabled = true;
        selector.appendChild(option);
    }
}

/**
 * Muestra una tendencia (▲ o ▼) en un elemento.
 */
function mostrarTendencia(elemento, porcentaje) {
    if (!elemento) return;
    
    elemento.className = "kpi-trend"; // Resetea
    const cambio = Number(porcentaje) || 0;

    if (cambio > 0) {
        elemento.textContent = `▲ ${cambio.toFixed(1)}%`;
        elemento.classList.add("positive");
    } else if (cambio < 0) {
        elemento.textContent = `▼ ${Math.abs(cambio).toFixed(1)}%`;
        elemento.classList.add("negative");
    } else {
        elemento.textContent = "0%";
    }
}

// --- Carga de KPIs ---

async function cargarKPIVentas(sucursalId = 'all') {
    const kpiEl = $("#kpi-ventas");
    const trendEl = $("#kpi-ventas-trend");
    if (!kpiEl || !trendEl) return;

    kpiEl.textContent = "...";
    trendEl.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/kpi_ventas?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });
        if (!response.ok) {
            if (response.status === 401 || response.status === 403) window.location.href = '/src/login.html';
            throw new Error("Error del servidor");
        }
        const data = await response.json();
        kpiEl.textContent = formatCLP(data.ventas_mes_actual);
        mostrarTendencia(trendEl, data.porcentaje_cambio);
    } catch (error) {
        console.error("Error cargando KPI de ventas:", error);
        kpiEl.textContent = "Error";
        trendEl.textContent = "N/A";
    }
}

async function cargarKPIPedidos(sucursalId = 'all') {
    const kpiEl = $("#kpi-pedidos");
    const trendEl = $("#kpi-pedidos-trend");
    if (!kpiEl || !trendEl) return;

    kpiEl.textContent = "...";
    trendEl.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/kpi_pedidos?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });
        if (!response.ok) throw new Error("Error del servidor");
        
        const data = await response.json();
        kpiEl.textContent = data.pedidos_mes_actual; // Es un conteo
        mostrarTendencia(trendEl, data.porcentaje_cambio);
    } catch (error) {
        console.error("Error cargando KPI de pedidos:", error);
        kpiEl.textContent = "Error";
        trendEl.textContent = "N/A";
    }
}

async function cargarKPIClientes(sucursalId = 'all') {
    const kpiEl = $("#kpi-clientes");
    const trendEl = $("#kpi-clientes-trend");
    if (!kpiEl || !trendEl) return;

    kpiEl.textContent = "...";
    trendEl.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/kpi_clientes?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });
        if (!response.ok) throw new Error("Error del servidor");
        
        const data = await response.json();
        kpiEl.textContent = data.clientes_mes_actual; // Es un conteo
        mostrarTendencia(trendEl, data.porcentaje_cambio);
    } catch (error) {
        console.error("Error cargando KPI de clientes:", error);
        kpiEl.textContent = "Error";
        trendEl.textContent = "N/A";
    }
}


// --- LÓGICA MODAL GRÁFICO (Ventas) ---
async function loadSalesChartData(sucursalId = 'all') {
    const ctx = document.getElementById('salesChartModalCanvas')?.getContext('2d');
    if (salesChart) salesChart.destroy();
    if (ctx) {
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        ctx.font = "16px sans-serif";
        ctx.fillStyle = "gray";
        ctx.textAlign = "center";
        ctx.fillText("Cargando datos...", ctx.canvas.width / 2, ctx.canvas.height / 2);
    }
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/ventas_mensuales?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });
        if (!response.ok) throw new Error("Error del servidor");
        const data = await response.json();
        currentChartData = data;
        renderSalesChart(currentChartType);
    } catch (error) {
        console.error("Error cargando datos del gráfico:", error);
        if (ctx) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
            ctx.fillStyle = "red";
            ctx.fillText("Error al cargar datos.", ctx.canvas.width / 2, ctx.canvas.height / 2);
        }
    }
}
function renderSalesChart(type = 'bar') {
    const ctx = document.getElementById('salesChartModalCanvas')?.getContext('2d');
    if (!ctx || !currentChartData) return;
    currentChartType = type;
    $all('.chart-type-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.type === type));
    if (salesChart) salesChart.destroy();
    let specificConfig = {};
    const datasets = JSON.parse(JSON.stringify(currentChartData.datasets));
    if (type === 'line') specificConfig = { type: 'line', data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: false})) } };
    else if (type === 'radar') specificConfig = { type: 'radar', data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: true})) } };
    else if (type === 'bar-stacked') specificConfig = { type: 'bar', data: { ...currentChartData, datasets }, options: { scales: { x: { stacked: true }, y: { stacked: true } } } };
    else if (type === 'line-filled') specificConfig = { type: 'line', data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: true})) } };
    else specificConfig = { type: 'bar', data: { ...currentChartData, datasets } };
    const baseConfig = {
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                title: { display: true, text: 'Ventas Mensuales (Año Actual vs. Año Pasado)', font: { size: 16 } },
                tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label || ''}: ${formatCLP(ctx.parsed.y)}` } }
            },
            scales: {
                y: { beginAtZero: true, max: 10000000, ticks: { stepSize: 1000000, callback: (val) => val === 0 ? '0' : `${val/1000000}M` } }
            }, ...specificConfig.options
        }
    };
    salesChart = new Chart(ctx, { type: specificConfig.type, data: specificConfig.data, options: baseConfig.options });
}
function openSalesChartModal() {
    $('#sales-chart-modal')?.classList.add('visible');
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadSalesChartData(sucursalId);
}
function closeSalesChartModal() {
    $('#sales-chart-modal')?.classList.remove('visible');
    if (salesChart) {
        salesChart.destroy();
        salesChart = null;
        currentChartData = null;
    }
}

// --- LÓGICA MODAL 1 (Lista Pedidos) ---
function openPedidosListModal() {
    $('#pedidos-list-modal')?.classList.add('visible');
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadPedidosListData(sucursalId);
}
function closePedidosListModal() {
    $('#pedidos-list-modal')?.classList.remove('visible');
    const tbody = $('#pedidos-modal-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
}
async function loadPedidosListData(sucursalId = 'all') {
    const tbody = $('#pedidos-modal-tbody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/lista_pedidos_mes?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor");
        const pedidos = await response.json();
        if (pedidos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="no-data">No se encontraron pedidos este mes.</td></tr>';
            return;
        }
        let html = '';
        pedidos.forEach(pedido => {
            const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''}`.trim();
            html += `
                <tr>
                    <td>#${pedido.id_pedido}</td>
                    <td><a href="#" class="pedido-detail-link" data-id-pedido="${pedido.id_pedido}">${nombreCompleto}</a></td>
                    <td>${pedido.total_items || 0}</td>
                </tr>`;
        });
        tbody.innerHTML = html;
    } catch (error) {
        console.error("Error cargando lista de pedidos:", error);
        tbody.innerHTML = `<tr><td colspan="3" class="no-data" style="color: red;">Error al cargar: ${error.message}</td></tr>`;
    }
}

// --- LÓGICA MODAL 2 (Detalle Pedido - de KPI) ---
function openPedidosDetailModal(id_pedido) {
    $('#pedidos-detail-modal')?.classList.add('visible');
    loadPedidoDetailData(id_pedido);
}
function closePedidosDetailModal() {
    $('#pedidos-detail-modal')?.classList.remove('visible');
    $all('#pedidos-detail-modal span[id^="detalle-"]').forEach(span => span.textContent = '...');
    const tbody = $('#detalle-items-tbody');
    if (tbody) tbody.innerHTML = '';
}
async function loadPedidoDetailData(id_pedido) {
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/detalle_pedido/${id_pedido}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor");
        const data = await response.json();
        const pedido = data.pedido;
        const items = data.items;
        const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''} ${pedido.apellido_materno || ''}`.trim();
        const direccionCompleta = `${pedido.calle || ''} ${pedido.numero_calle || ''}`.trim();
        $('#detalle-cliente-nombre').textContent = nombreCompleto;
        $('#detalle-cliente-email').textContent = pedido.email_usuario || 'N/A';
        $('#detalle-cliente-telefono').textContent = pedido.telefono || 'N/A';
        $('#detalle-cliente-direccion').textContent = direccionCompleta || 'N/A';
        $('#detalle-cliente-comuna').textContent = pedido.comuna || 'N/A';
        $('#detalle-cliente-ciudad').textContent = pedido.ciudad || 'N/A';
        $('#detalle-cliente-region').textContent = pedido.region || 'N/A';
        $('#detalle-pedido-id').textContent = pedido.id_pedido;
        $('#detalle-pedido-id-2').textContent = pedido.id_pedido;
        $('#detalle-pedido-fecha').textContent = formatFecha(pedido.creado_en);
        $('#detalle-pedido-total').textContent = formatCLP(pedido.total);
        $('#detalle-pedido-metodo').textContent = pedido.metodo_pago || 'N/A';
        $('#detalle-pedido-estado').textContent = pedido.estado_pedido || 'N/A';
        $('#detalle-pedido-transaccion').textContent = pedido.transaccion_id || 'N/A';
        
        const itemsTbody = $('#detalle-items-tbody');
        let itemsHtml = '';
        if (items.length > 0) {
            items.forEach(item => {
                itemsHtml += `
                    <tr>
                        <td><img src="${item.imagen_url || '../Public/img/placeholder.png'}" alt="${item.nombre_producto}" class="item-foto"></td>
                        <td>${item.nombre_producto || 'Producto no encontrado'}</td>
                        <td>${item.sku_producto || 'N/A'}</td>
                        <td>${item.talla || 'Única'}</td>
                        <td>${item.color || 'N/A'}</td>
                        <td>${item.cantidad}</td>
                        <td>${formatCLP(item.precio_unitario)}</td>
                    </tr>`;
            });
        } else {
            itemsHtml = '<tr><td colspan="7" class="no-data">No se encontraron items para este pedido.</td></tr>'; // Colspan es 7 ahora
        }
        itemsTbody.innerHTML = itemsHtml;
    } catch (error) {
        console.error(`Error cargando detalle del pedido ${id_pedido}:`, error);
        $('#detalle-cliente-nombre').textContent = `Error: ${error.message}`;
    }
}


// --- LÓGICA MODALES CLIENTES ---
function openClientesListModal() {
    $('#clientes-list-modal')?.classList.add('visible');
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadClientesListData(sucursalId);
}
function closeClientesListModal() {
    $('#clientes-list-modal')?.classList.remove('visible');
    const tbody = $('#clientes-modal-tbody');
    const thead = $('#clientes-modal-thead');
    if (tbody) tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
    if (thead) thead.innerHTML = '';
}
async function loadClientesListData(sucursalId = 'all') {
    const tbody = $('#clientes-modal-tbody');
    const thead = $('#clientes-modal-thead');
    if (!tbody || !thead) return;
    const esTodasSucursales = (sucursalId === 'all');
    if (esTodasSucursales) {
        thead.innerHTML = `<tr><th>Nombre Cliente</th><th>Email</th><th>Fecha Registro</th></tr>`;
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
    } else {
        thead.innerHTML = `<tr><th>Nombre Cliente</th><th>Email</th><th>Dirección</th></tr>`;
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
    }
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/lista_nuevos_clientes?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor");
        const clientes = await response.json();
        if (clientes.length === 0) {
            tbody.innerHTML = `<tr><td colspan="3" class="no-data">No se encontraron nuevos clientes.</td></tr>`;
            return;
        }
        let html = '';
        clientes.forEach(cliente => {
            const nombreCompleto = `${cliente.nombre_usuario || ''} ${cliente.apellido_paterno || ''}`.trim();
            html += `<tr>`;
            html += `<td><a href="#" class="cliente-detail-link" data-id-cliente="${cliente.id_usuario}">${nombreCompleto}</a></td>`;
            html += `<td>${cliente.email_usuario}</td>`;
            if (esTodasSucursales) {
                html += `<td>${formatFecha(cliente.creado_en)}</td>`;
            } else {
                const direccion = `${cliente.region || ''}, ${cliente.ciudad || ''}, ${cliente.comuna || ''}, ${cliente.calle || ''} ${cliente.numero_calle || ''}`;
                html += `<td>${direccion.replace(/, ,/g, ',').replace(/^, | ,$/g, '')}</td>`;
            }
            html += `</tr>`;
        });
        tbody.innerHTML = html;
    } catch (error) {
        console.error("Error cargando lista de clientes:", error);
        tbody.innerHTML = `<tr><td colspan="3" class="no-data" style="color: red;">Error al cargar: ${error.message}</td></tr>`;
    }
}
function openClienteDetailModal(id_cliente) {
    $('#clientes-detail-modal')?.classList.add('visible');
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadClienteDetailData(id_cliente, sucursalId);
}
function closeClienteDetailModal() {
    $('#clientes-detail-modal')?.classList.remove('visible');
    $all('#clientes-detail-modal span[id^="detalle-cliente-"]').forEach(span => span.textContent = '...');
    const tbody = $('#cliente-pedidos-tbody');
    if (tbody) tbody.innerHTML = '';
}
async function loadClienteDetailData(id_cliente, sucursalId) {
    $all('#clientes-detail-modal span[id^="detalle-cliente-"]').forEach(span => span.textContent = '...');
    const pedidosTbody = $('#cliente-pedidos-tbody');
    if (pedidosTbody) pedidosTbody.innerHTML = '<tr><td colspan="6" class="no-data">Cargando...</td></tr>';
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/historial_cliente/${id_cliente}?sucursal_id=${sucursalId}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor");
        const data = await response.json();
        const usuario = data.usuario;
        const pedidos = data.pedidos;
        const nombreCompleto = `${usuario.nombre_usuario || ''} ${usuario.apellido_paterno || ''} ${usuario.apellido_materno || ''}`.trim();
        const direccionCompleta = `${usuario.region || ''}, ${usuario.ciudad || ''}, ${usuario.comuna || ''}, ${usuario.calle || ''} ${usuario.numero_calle || ''}`;
        $('#detalle-cliente-nombre-modal').textContent = nombreCompleto;
        $('#detalle-cliente-nombre-2').textContent = nombreCompleto;
        $('#detalle-cliente-email-2').textContent = usuario.email_usuario || 'N/A';
        $('#detalle-cliente-direccion-2').textContent = direccionCompleta.replace(/, ,/g, ',').replace(/^, | ,$/g, '') || 'N/A';
        $('#detalle-cliente-total-pedidos').textContent = data.total_pedidos || 0;
        if (pedidos.length === 0) {
            pedidosTbody.innerHTML = '<tr><td colspan="6" class="no-data">Este cliente no tiene pedidos.</td></tr>';
            return;
        }
        let pedidosHtml = '';
        pedidos.forEach(pedido => {
            pedidosHtml += `
                <tr>
                    <td>#${pedido.id_pedido}</td>
                    <td>${formatFecha(pedido.creado_en)}</td>
                    <td>${pedido.nombre_sucursal || 'N/A'}</td>
                    <td style="font-size: 0.8em; max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${pedido.productos_preview || ''}">
                        ${pedido.productos_preview || 'N/A'}
                    </td>
                    <td>${formatCLP(pedido.total)}</td>
                    <td><a href="#" class="pedido-detail-link" data-id-pedido="${pedido.id_pedido}">Ver</a></td>
                </tr>`;
        });
        pedidosTbody.innerHTML = pedidosHtml;
    } catch (error) {
        console.error(`Error cargando historial del cliente ${id_cliente}:`, error);
        pedidosTbody.innerHTML = `<tr><td colspan="6" class="no-data" style="color: red;">Error al cargar: ${error.message}</td></tr>`;
    }
}

// --- LÓGICA PARA MODAL DE GENERAR INFORME ---

function openReportOptionsModal() {
    $('#report-options-modal')?.classList.add('visible');
}

function closeReportOptionsModal() {
    $('#report-options-modal')?.classList.remove('visible');
    const form = $('#report-options-form');
    if(form) form.reset();
}

async function handleReportGeneration(e) {
    e.preventDefault();
    const btn = $('#generate-report-submit-btn');
    if (!btn) return;
    
    btn.textContent = 'Generando...';
    btn.disabled = true;

    try {
        const form = e.target;
        const formData = new FormData(form);
        const tipo_reporte = formData.get('tipo_reporte');
        const mes = formData.get('mes');
        const sucursal_id = $("#admin-sucursal-selector")?.value || 'all';

        if (!tipo_reporte) {
            alert('Por favor, seleccione un tipo de informe.');
            throw new Error("Tipo de informe no seleccionado");
        }

        const url = new URL(`${API_BACKEND}/api/admin/reportes/generar_informe`);
        url.searchParams.append('tipo_reporte', tipo_reporte);
        url.searchParams.append('mes', mes);
        url.searchParams.append('sucursal_id', sucursal_id);

        const response = await fetch(url, { credentials: 'include' });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "No se pudo generar el informe");
        }

        const disposition = response.headers.get('Content-Disposition');
        let filename = 'reporte.csv';
        if (disposition && disposition.indexOf('attachment') !== -1) {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) {
                filename = matches[1].replace(/['"]/g, '');
            }
        }

        const blob = await response.blob();
        const a = document.createElement('a');
        a.href = window.URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        a.remove();
        window.URL.revokeObjectURL(a.href);
        
        closeReportOptionsModal();

    } catch (error) {
        console.error("Error al generar el informe:", error);
        alert(`Error: ${error.message}`);
    } finally {
        btn.textContent = 'Descargar CSV';
        btn.disabled = false;
    }
}

// --- ▼▼▼ FUNCIONES ACTUALIZADAS PARA PEDIDOS RECIENTES ▼▼▼ ---

/**
 * Carga la tabla de "Pedidos Recientes" en el dashboard.
 */
async function loadPedidosRecientes(sucursalId = 'all', limit = 10) {
    const tbody = $("#pedidos-recientes-tbody");
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="9" class="no-data">Cargando...</td></tr>`; // Colspan 9

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/pedidos_recientes?sucursal_id=${sucursalId}&limit=${limit}`, {
            credentials: "include"
        });

        if (!response.ok) {
             const err = await response.json();
             throw new Error(err.error || "Error del servidor");
        }
        
        const pedidos = await response.json();

        if (pedidos.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="no-data">No se encontraron pedidos.</td></tr>`;
            return;
        }

        let html = '';
        pedidos.forEach(pedido => {
            const nombreCompleto = `${pedido.cliente_nombre || ''}`.trim();
            
            // --- Lógica para Estado de Pago (CORREGIDA) ---
            let pagoEstado = pedido.estado_pago;
            let pagoClass = 'bg-secondary'; // Default gris

            if (pagoEstado === 'aprobado') {
                pagoClass = 'bg-success';
            } else if (pagoEstado === 'rechazado') {
                pagoClass = 'bg-danger';
            } else {
                // Si es null, undefined, o cualquier otra cosa
                pagoEstado = 'Pendiente'; 
                pagoClass = 'bg-warning';
            }
            // --- Fin Lógica Estado Pago ---

            // --- Lógica para Estado de Pedido (Envío) ---
            let pedidoEstado = pedido.estado_pedido || 'N/A';
            let pedidoClass = 'bg-secondary'; // Default
            if (pedidoEstado === 'pagado') {
                pedidoEstado = 'Por despachar';
                pedidoClass = 'bg-info';
            } else if (pedidoEstado === 'enviado') {
                pedidoClass = 'bg-primary';
            } else if (pedidoEstado === 'entregado') {
                pedidoClass = 'bg-success';
            } else if (pedidoEstado === 'pendiente') { // Pendiente de pago
                pedidoEstado = 'Pendiente Pago';
                pedidoClass = 'bg-warning';
            } else if (pedidoEstado === 'rechazado') {
                pedidoClass = 'bg-danger';
            }
            
            html += `
                <tr>
                    <td>#${pedido.id_pedido}</td>
                    <td>${nombreCompleto || 'N/A'}</td>
                    <td>${pedido.email || 'N/A'}</td>
                    <td>${pedido.telefono || 'N/A'}</td>
                    <td>${formatFecha(pedido.creado_en)}</td>
                    <td><span class="badge ${pagoClass}">${pagoEstado}</span></td>
                    <td><span class="badge ${pedidoClass}">${pedidoEstado}</span></td>
                    <td>${formatCLP(pedido.total)}</td>
                    <td>
                        <button class="admin-btn-sm" data-id-pedido="${pedido.id_pedido}">
                            Ver detalle
                        </button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;

    } catch (error) {
        console.error("Error cargando pedidos recientes:", error);
        tbody.innerHTML = `<tr><td colspan="9" class="no-data" style="color: red;">${error.message}</td></tr>`;
    }
}

/**
 * Abre el modal de detalle para un pedido reciente.
 */
function openRecentOrderDetailModal(id_pedido) {
    const modal = $('#recent-order-detail-modal');
    if (modal) {
        modal.classList.add('visible');
        loadRecentOrderDetailData(id_pedido); 
    }
}

/**
 * Cierra el modal de detalle del pedido reciente.
 */
function closeRecentOrderDetailModal() {
    const modal = $('#recent-order-detail-modal');
    if (modal) {
        modal.classList.remove('visible');
        // Limpiar spans
        $all('#recent-order-detail-modal span[id^="recent-detalle-"]').forEach(span => {
            span.textContent = '...';
        });
        // Limpiar tabla
        const tbody = $('#recent-detalle-items-tbody');
        if (tbody) tbody.innerHTML = '';
    }
}

/**
 * Carga los datos en el modal de detalle del pedido reciente.
 * Utiliza el mismo endpoint que el otro modal de detalle de pedido.
 */
async function loadRecentOrderDetailData(id_pedido) {
    try {
        // Usamos el endpoint de detalle de pedido existente, que ya trae los items.
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/detalle_pedido/${id_pedido}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor");
        
        const data = await response.json();
        const pedido = data.pedido;
        const items = data.items;

        const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''} ${pedido.apellido_materno || ''}`.trim();
        const direccionCompleta = `${pedido.calle || ''} ${pedido.numero_calle || ''}`.trim() || 'No especificada';

        // Poblar datos del cliente
        $('#recent-detalle-cliente-nombre').textContent = nombreCompleto;
        $('#recent-detalle-cliente-email').textContent = pedido.email_usuario || 'N/A';
        $('#recent-detalle-cliente-telefono').textContent = pedido.telefono || 'N/A';
        $('#recent-detalle-cliente-direccion').textContent = direccionCompleta;
        $('#recent-detalle-cliente-comuna').textContent = pedido.comuna || 'N/A';
        $('#recent-detalle-cliente-ciudad').textContent = pedido.ciudad || 'N/A';
        $('#recent-detalle-cliente-region').textContent = pedido.region || 'N/A';

        // Poblar datos del pedido
        $('#recent-detalle-pedido-id').textContent = pedido.id_pedido;
        $('#recent-detalle-pedido-id-2').textContent = pedido.id_pedido;
        $('#recent-detalle-pedido-fecha').textContent = formatFecha(pedido.creado_en);
        $('#recent-detalle-pedido-total').textContent = formatCLP(pedido.total);
        $('#recent-detalle-pedido-metodo').textContent = pedido.metodo_pago || 'N/A';
        
        // --- Lógica de Estado de Pago y Pedido (CORREGIDA) ---
        const estadoPago = pedido.metodo_pago ? (pedido.estado_pedido === 'rechazado' ? 'Rechazado' : 'Aprobado') : 'Pendiente';
        $('#recent-detalle-pedido-estado').textContent = estadoPago;

        let estadoPedido = pedido.estado_pedido;
        if (estadoPedido === 'pagado') {
            estadoPedido = 'Por despachar';
        }
        $('#recent-detalle-envio-estado').textContent = estadoPedido;


        // Poblar items
        const itemsTbody = $('#recent-detalle-items-tbody');
        let itemsHtml = '';
        if (items.length > 0) {
            items.forEach(item => {
                itemsHtml += `
                    <tr>
                        <td><img src="${item.imagen_url || '../Public/img/placeholder.png'}" alt="${item.nombre_producto}" class="item-foto"></td>
                        <td>${item.nombre_producto || 'Producto no encontrado'}</td>
                        <td>${item.sku_producto || 'N/A'}</td>
                        <td>${item.talla || 'Única'}</td>
                        <td>${item.color || 'N/A'}</td>
                        <td>${item.cantidad}</td>
                        <td>${formatCLP(item.precio_unitario)}</td>
                    </tr>`;
            });
        } else {
            itemsHtml = '<tr><td colspan="7" class="no-data">No se encontraron items para este pedido.</td></tr>'; // Colspan 7
        }
        itemsTbody.innerHTML = itemsHtml;

    } catch (error) {
        console.error(`Error cargando detalle del pedido ${id_pedido}:`, error);
        $('#recent-detalle-cliente-nombre').textContent = `Error: ${error.message}`;
    }
}
// --- ▲▲▲ FIN NUEVAS FUNCIONES ▲▲▲ ---


// --- Evento Principal (MODIFICADO) ---
document.addEventListener("DOMContentLoaded", () => {
    // Selectores
    const selectorSucursal = $("#admin-sucursal-selector");
    const sidebarToggle = $("#sidebarToggle");
    const sidebar = $("#adminSidebar");
    
    // Selectores: Modales de Ventas
    const kpiVentasCard = $("#kpi-ventas-card");
    const modalCloseBtn = $("#modal-close-btn");
    const modalOverlay = $("#sales-chart-modal");
    const chartTypeButtons = $all('.chart-type-btn');
    
    // Selectores: Modales de Pedidos (KPI)
    const kpiPedidosCard = $("#kpi-pedidos-card");
    const pedidosListModal = $("#pedidos-list-modal");
    const pedidosListCloseBtn = $("#pedidos-list-close-btn");
    const pedidosListBody = $("#pedidos-modal-tbody");
    const pedidosDetailModal = $("#pedidos-detail-modal");
    const pedidosDetailCloseBtn = $("#pedidos-detail-close-btn");
    
    // Selectores: Modales de Clientes
    const kpiClientesCard = $("#kpi-clientes-card");
    const clientesListModal = $("#clientes-list-modal");
    const clientesListCloseBtn = $("#clientes-list-close-btn");
    const clientesListBody = $("#clientes-modal-tbody");
    const clientesDetailModal = $("#clientes-detail-modal");
    const clientesDetailCloseBtn = $("#clientes-detail-close-btn");
    const clientePedidosBody = $("#cliente-pedidos-tbody");
    
    // Selectores: Modal de Informe
    const openReportBtn = $("#open-report-modal-btn");
    const reportOptionsModal = $("#report-options-modal");
    const reportOptionsCloseBtn = $("#report-options-close-btn");
    const reportOptionsForm = $("#report-options-form");

    // --- ▼▼▼ NUEVOS Selectores para Pedidos Recientes ▼▼▼ ---
    const pedidosRecientesTbody = $("#pedidos-recientes-tbody");
    const pedidosLimitSelector = $("#pedidos-limit-selector");
    const recentOrderDetailModal = $("#recent-order-detail-modal");
    const recentOrderDetailCloseBtn = $("#recent-order-detail-close-btn");
    // --- ▲▲▲ FIN NUEVOS Selectores ▲▲▲ ---

    // 1. Cargar el selector de sucursales
    cargarSucursales();

    // 2. Cargar los KPIs iniciales (para "Todas las sucursales")
    cargarKPIVentas('all');
    cargarKPIPedidos('all');
    cargarKPIClientes('all');
    
    // --- ▼▼▼ NUEVO: Cargar tabla de pedidos recientes al inicio ▼▼▼ ---
    loadPedidosRecientes('all', 10); // Carga 10 por defecto
    
    // 3. Listener para el selector de sucursal
    if (selectorSucursal) {
        selectorSucursal.addEventListener("change", () => {
            const sucursalIdSeleccionada = selectorSucursal.value;
            const currentLimit = pedidosLimitSelector?.value || 10; // <-- Obtener límite
            
            // Recargar KPIs
            cargarKPIVentas(sucursalIdSeleccionada);
            cargarKPIPedidos(sucursalIdSeleccionada);
            cargarKPIClientes(sucursalIdSeleccionada);
            
            // --- ▼▼▼ MODIFICADO: Recargar Pedidos Recientes ▼▼▼ ---
            loadPedidosRecientes(sucursalIdSeleccionada, currentLimit);
            
            // Recargar modales abiertos
            if (modalOverlay?.classList.contains('visible')) loadSalesChartData(sucursalIdSeleccionada);
            if (pedidosListModal?.classList.contains('visible')) loadPedidosListData(sucursalIdSeleccionada);
            if (clientesListModal?.classList.contains('visible')) loadClientesListData(sucursalIdSeleccionada);
        });
    }
    
    // 4. Listeners para el Modal de Ventas (Gráfico)
    kpiVentasCard?.addEventListener('click', openSalesChartModal);
    modalCloseBtn?.addEventListener('click', closeSalesChartModal);
    modalOverlay?.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeSalesChartModal();
    });
    chartTypeButtons.forEach(btn => {
        btn.addEventListener('click', () => renderSalesChart(btn.dataset.type));
    });

    // 5. Listeners para Modales de Pedidos (KPI)
    kpiPedidosCard?.addEventListener('click', openPedidosListModal);
    pedidosListCloseBtn?.addEventListener('click', closePedidosListModal);
    pedidosListModal?.addEventListener('click', (e) => {
        if (e.target === pedidosListModal) closePedidosListModal();
    });
    pedidosListBody?.addEventListener('click', (e) => {
        const link = e.target.closest('.pedido-detail-link');
        if (link) {
            e.preventDefault();
            const idPedido = link.dataset.idPedido; 
            if (idPedido) openPedidosDetailModal(idPedido);
        }
    });
    pedidosDetailCloseBtn?.addEventListener('click', closePedidosDetailModal);
    pedidosDetailModal?.addEventListener('click', (e) => {
        if (e.target === pedidosDetailModal) closePedidosDetailModal();
    });

    // 6. Listeners para Modales de Clientes
    kpiClientesCard?.addEventListener('click', openClientesListModal);
    clientesListCloseBtn?.addEventListener('click', closeClientesListModal);
    clientesListModal?.addEventListener('click', (e) => {
        if (e.target === clientesListModal) closeClientesListModal();
    });
    clientesListBody?.addEventListener('click', (e) => {
        const link = e.target.closest('.cliente-detail-link');
        if (link) {
            e.preventDefault();
            const idCliente = link.dataset.idCliente;
            if (idCliente) openClienteDetailModal(idCliente);
        }
    });
    clientesDetailCloseBtn?.addEventListener('click', closeClienteDetailModal);
    clientesDetailModal?.addEventListener('click', (e) => {
        if (e.target === clientesDetailModal) closeClienteDetailModal();
    });
    clientePedidosBody?.addEventListener('click', (e) => {
        const link = e.target.closest('.pedido-detail-link');
        if (link) {
            e.preventDefault();
            const idPedido = link.dataset.idPedido;
            if (idPedido) openPedidosDetailModal(idPedido);
        }
    });
    
    // 7. Listeners para Modal de Informe
    openReportBtn?.addEventListener('click', openReportOptionsModal);
    reportOptionsCloseBtn?.addEventListener('click', closeReportOptionsModal);
    reportOptionsModal?.addEventListener('click', (e) => {
        if (e.target === reportOptionsModal) closeReportOptionsModal();
    });
    reportOptionsForm?.addEventListener('submit', handleReportGeneration);

    // 8. Lógica del sidebar (existente)
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    // --- ▼▼▼ NUEVOS Listeners para Pedidos Recientes ▼▼▼ ---
    
    // Listener para el filtro de límite
    pedidosLimitSelector?.addEventListener('change', () => {
        const sucursalId = selectorSucursal?.value || 'all';
        const limit = pedidosLimitSelector.value;
        loadPedidosRecientes(sucursalId, limit);
    });

    // Listener para los botones "Ver detalle" en la tabla
    pedidosRecientesTbody?.addEventListener('click', (e) => {
        const boton = e.target.closest('.admin-btn-sm');
        if (boton) {
            e.preventDefault();
            const idPedido = boton.dataset.idPedido;
            if (idPedido) {
                openRecentOrderDetailModal(idPedido);
            }
        }
    });

    // Listeners para cerrar el nuevo modal
    recentOrderDetailCloseBtn?.addEventListener('click', closeRecentOrderDetailModal);
    recentOrderDetailModal?.addEventListener('click', (e) => {
        if (e.target === recentOrderDetailModal) {
            closeRecentOrderDetailModal();
        }
    });
    // --- ▲▲▲ FIN NUEVOS Listeners ▲▲▲ ---
});