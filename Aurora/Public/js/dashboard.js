// ../Public/js/dashboard.js

// NOTA: Asumo que 'colores.js' maneja el sidebar, así que este
// archivo se enfoca solo en los KPIs y modales de "Ventas hoy".

// URL del backend
const API_BACKEND = "http://localhost:5000";

// --- Selectores ---
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Card KPI
const kpiVentasCard = $("#kpi-ventas-hoy-card");
const kpiVentasMonto = $("#kpi-ventas-hoy-monto");
const kpiVentasTrend = $("#kpi-ventas-hoy-trend");

// Modal 1 (Chart y Lista)
const salesChartModal = $("#sales-chart-modal");
const salesChartCloseBtn = $("#sales-chart-close-btn");
const salesComparisonFilter = $("#sales-comparison-filter");
const salesListTbody = $("#sales-list-tbody");
const salesChartCanvas = $("#salesChartCanvas");

// Modal 2 (Detalle Pedido)
const pedidosDetailModal = $("#pedidos-detail-modal");
const pedidosDetailCloseBtn = $("#pedidos-detail-close-btn");

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
 * Carga el KPI principal de "Ventas hoy" y la comparación vs. ayer.
 */
async function loadKPIVentasHoy() {
    if (!kpiVentasMonto || !kpiVentasTrend) return;

    kpiVentasMonto.textContent = "...";
    kpiVentasTrend.textContent = "...";

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/kpi_ventas_hoy`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar KPI de ventas.");
        
        const data = await response.json();
        
        kpiVentasMonto.textContent = formatCLP(data.ventas_hoy);
        
        const trend = data.porcentaje_vs_ayer;
        kpiVentasTrend.className = "kpi-trend"; // Reset
        if (trend > 0) {
            kpiVentasTrend.textContent = `▲ ${trend.toFixed(0)}%`;
            kpiVentasTrend.classList.add("positive");
        } else if (trend < 0) {
            kpiVentasTrend.textContent = `▼ ${Math.abs(trend).toFixed(0)}%`;
            kpiVentasTrend.classList.add("negative");
        } else {
            kpiVentasTrend.textContent = "0%";
            kpiVentasTrend.classList.add("neutral");
        }

    } catch (error) {
        console.error("Error en loadKPIVentasHoy:", error);
        kpiVentasMonto.textContent = "Error";
        kpiVentasTrend.textContent = "N/A";
    }
}

/**
 * Carga los datos para el gráfico de comparación en el Modal 1.
 */
async function loadVentasChart(periodo = 'ayer') {
    if (!salesChartCanvas) return;

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/chart_ventas?periodo=${periodo}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar datos del gráfico.");
        
        const data = await response.json();

        // Destruir gráfico anterior si existe
        if (salesChart) {
            salesChart.destroy();
        }

        // Crear nuevo gráfico
        const ctx = salesChartCanvas.getContext('2d');
        salesChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.labels, // Ej: ["Hoy", "Ayer"]
                datasets: [
                    {
                        label: 'Ventas',
                        data: data.data, // Ej: [50000, 45000]
                        backgroundColor: [
                            'rgba(13, 110, 253, 0.7)', // Hoy (Azul)
                            'rgba(108, 117, 125, 0.7)' // Comparación (Gris)
                        ],
                        borderColor: [
                            'rgba(13, 110, 253, 1)',
                            'rgba(108, 117, 125, 1)'
                        ],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Ventas: ${formatCLP(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                // Formato corto para el eje Y
                                if (value >= 1000000) return `$${value / 1000000}M`;
                                if (value >= 1000) return `$${value / 1000}k`;
                                return formatCLP(value);
                            }
                        }
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
async function loadVentasHoyList() {
    if (!salesListTbody) return;

    salesListTbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Cargando...</td></tr>';

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/dashboard/lista_ventas_hoy`, { credentials: "include" });
        if (!response.ok) throw new Error("Error al cargar la lista de ventas.");

        const ventas = await response.json();

        if (ventas.length === 0) {
            salesListTbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No se encontraron ventas hoy.</td></tr>';
            return;
        }

        let html = '';
        ventas.forEach(venta => {
            // Extraer solo la hora
            const hora = formatFecha(venta.creado_en, true).split(' ')[1] + (formatFecha(venta.creado_en, true).split(' ')[2] || '');
            html += `
                <tr>
                    <td>#${venta.id_pedido}</td>
                    <td>${venta.cliente_nombre || 'N/A'}</td>
                    <td>${venta.productos_preview || 'Sin detalle'}...</td>
                    <td>${hora || 'N/A'}</td>
                    <td>
                        <a href="#" class="sale-detail-link" data-id-pedido="${venta.id_pedido}">
                            Ver detalle
                        </a>
                    </td>
                </tr>
            `;
        });
        salesListTbody.innerHTML = html;

    } catch (error) {
        console.error("Error en loadVentasHoyList:", error);
        salesListTbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: red;">Error al cargar la lista.</td></tr>`;
    }
}

// --- Lógica para Modal 2 (Detalle Pedido) ---
// (Reutilizada de reportes_admin.js y adaptada)

function openPedidosDetailModal(id_pedido) {
    if (pedidosDetailModal) {
        pedidosDetailModal.classList.add('visible');
        loadPedidoDetailData(id_pedido);
    }
}

function closePedidosDetailModal() {
    if (pedidosDetailModal) {
        pedidosDetailModal.classList.remove('visible');
        // Limpiar campos
        $all('#pedidos-detail-modal span[id^="detalle-"]').forEach(span => span.textContent = '...');
        const tbody = $('#detalle-items-tbody');
        if (tbody) tbody.innerHTML = '<tr><td colspan="7" class="text-center">...</td></tr>';
    }
}

async function loadPedidoDetailData(id_pedido) {
    try {
        // Reutilizamos el endpoint de reportes, es perfecto para esto.
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/detalle_pedido/${id_pedido}`, { credentials: "include" });
        if (!response.ok) throw new Error("Error del servidor al buscar detalle.");
        
        const data = await response.json();
        const pedido = data.pedido;
        const items = data.items;

        if (!pedido) {
             throw new Error("El pedido no se encontró o no tiene datos.");
        }

        const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''} ${pedido.apellido_materno || ''}`.trim();
        const direccionCompleta = `${pedido.calle || ''} ${pedido.numero_calle || ''}`.trim();
        
        // Llenar Datos Cliente
        $('#detalle-cliente-nombre').textContent = nombreCompleto;
        $('#detalle-cliente-email').textContent = pedido.email_usuario || 'N/A';
        $('#detalle-cliente-telefono').textContent = pedido.telefono || 'N/A';
        $('#detalle-cliente-direccion').textContent = direccionCompleta || 'No especificada';
        $('#detalle-cliente-comuna').textContent = pedido.comuna || 'N/A';
        $('#detalle-cliente-ciudad').textContent = pedido.ciudad || 'N/A';
        $('#detalle-cliente-region').textContent = pedido.region || 'N/A';
        
        // Llenar Datos Pedido
        $('#detalle-pedido-id').textContent = pedido.id_pedido;
        $('#detalle-pedido-id-2').textContent = pedido.id_pedido;
        $('#detalle-pedido-sucursal').textContent = pedido.nombre_sucursal || 'No especificada'; // Asumiendo que la query lo trae
        $('#detalle-pedido-fecha').textContent = formatFecha(pedido.creado_en, true);
        $('#detalle-pedido-total').textContent = formatCLP(pedido.total);
        $('#detalle-pedido-metodo').textContent = pedido.metodo_pago || 'N/A';

        // Lógica de Estados
        let estadoPago = 'Pendiente';
        if (pedido.estado_pedido === 'rechazado') {
            estadoPago = 'Rechazado';
        } else if (pedido.metodo_pago) {
            estadoPago = 'Aprobado';
        }
        $('#detalle-pedido-estado-pago').textContent = estadoPago;

        let estadoPedido = pedido.estado_pedido;
        if (estadoPedido === 'pagado') {
            estadoPedido = 'Por despachar';
        }
        $('#detalle-pedido-estado-pedido').textContent = estadoPedido;

        // Llenar Items
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


// --- Inicialización y Listeners ---
document.addEventListener("DOMContentLoaded", () => {
    
    // Carga inicial del KPI
    loadKPIVentasHoy();

    // Listener para abrir Modal 1 (Gráfico/Lista)
    kpiVentasCard?.addEventListener('click', () => {
        salesChartModal?.classList.add('visible');
        // Cargar datos al abrir
        loadVentasChart('ayer'); // Carga el gráfico por defecto
        loadVentasHoyList(); // Carga la lista
    });

    // Listener para cerrar Modal 1
    salesChartCloseBtn?.addEventListener('click', () => {
        salesChartModal?.classList.remove('visible');
    });
    salesChartModal?.addEventListener('click', (e) => {
        if (e.target === salesChartModal) salesChartModal.classList.remove('visible');
    });


    // Listener para el filtro del gráfico
    salesComparisonFilter?.addEventListener('change', (e) => {
        loadVentasChart(e.target.value);
    });

    // Listener de clic en la lista de ventas (para abrir Modal 2)
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

    // Listener para cerrar Modal 2
    pedidosDetailCloseBtn?.addEventListener('click', () => {
        closePedidosDetailModal();
    });
    pedidosDetailModal?.addEventListener('click', (e) => {
        if (e.target === pedidosDetailModal) closePedidosDetailModal();
    });
});