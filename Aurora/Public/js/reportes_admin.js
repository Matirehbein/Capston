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

// --- ▼▼▼ NUEVO: Helper para formatear fechas ▼▼▼ ---
/**
 * Formatea una fecha ISO (o de DB) a un formato legible.
 */
function formatFecha(isoString) {
    if (!isoString) return "N/A";
    try {
        const date = new Date(isoString);
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
// --- ▲▲▲ FIN NUEVO Helper ▲▲▲ ---

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
 * Busca los datos del KPI de Ventas en la API
 * según la sucursal seleccionada.
 */
async function cargarKPIVentas(sucursalId = 'all') {
  console.log(`Cargando KPI de ventas para sucursal: ${sucursalId}`);
  const kpiVentasEl = $("#kpi-ventas");
  const kpiTrendEl = $("#kpi-ventas-trend");

  if (!kpiVentasEl || !kpiTrendEl) return;

  // Estado de carga
  kpiVentasEl.textContent = "...";
  kpiTrendEl.textContent = "...";
  kpiTrendEl.className = "kpi-trend"; // Resetea clases positive/negative

  try {
    const response = await fetch(`${API_BACKEND}/api/admin/reportes/kpi_ventas?sucursal_id=${sucursalId}`, {
        credentials: "include" // Enviar cookies de sesión de admin
    });
    
    if (!response.ok) {
        const err = await response.json();
        if (response.status === 401 || response.status === 403) {
            window.location.href = '/src/login.html';
        }
        throw new Error(err.error || "Error del servidor");
    }
    
    const data = await response.json();

    kpiVentasEl.textContent = formatCLP(data.ventas_mes_actual);
    
    const cambio = data.porcentaje_cambio;
    if (cambio > 0) {
      kpiTrendEl.textContent = `▲ ${cambio.toFixed(1)}%`;
      kpiTrendEl.classList.add("positive");
    } else if (cambio < 0) {
      kpiTrendEl.textContent = `▼ ${Math.abs(cambio).toFixed(1)}%`;
      kpiTrendEl.classList.add("negative");
    } else {
      kpiTrendEl.textContent = "0%";
    }

  } catch (error) {
    console.error("Error cargando KPI de ventas:", error);
    kpiVentasEl.textContent = "Error";
    kpiTrendEl.textContent = "N/A";
  }
}


// --- ▼▼▼ NUEVA FUNCIÓN: Cargar KPI de Pedidos ▼▼▼ ---
/**
 * Busca los datos del KPI de Pedidos en la API
 * según la sucursal seleccionada.
 */
async function cargarKPIPedidos(sucursalId = 'all') {
  console.log(`Cargando KPI de pedidos para sucursal: ${sucursalId}`);
  const kpiPedidosEl = $("#kpi-pedidos");
  const kpiTrendEl = $("#kpi-pedidos-trend"); // Usamos el nuevo ID del HTML

  if (!kpiPedidosEl || !kpiTrendEl) return;

  // Estado de carga
  kpiPedidosEl.textContent = "...";
  kpiTrendEl.textContent = "...";
  kpiTrendEl.className = "kpi-trend"; // Resetea clases

  try {
    const response = await fetch(`${API_BACKEND}/api/admin/reportes/kpi_pedidos?sucursal_id=${sucursalId}`, {
        credentials: "include"
    });
    
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.error || "Error del servidor");
    }
    
    const data = await response.json();

    // Es un conteo, no moneda
    kpiPedidosEl.textContent = data.pedidos_mes_actual; 
    
    const cambio = data.porcentaje_cambio;
    if (cambio > 0) {
      kpiTrendEl.textContent = `▲ ${cambio.toFixed(1)}%`;
      kpiTrendEl.classList.add("positive");
    } else if (cambio < 0) {
      kpiTrendEl.textContent = `▼ ${Math.abs(cambio).toFixed(1)}%`;
      kpiTrendEl.classList.add("negative");
    } else {
      kpiTrendEl.textContent = "0%";
    }

  } catch (error) {
    console.error("Error cargando KPI de pedidos:", error);
    kpiPedidosEl.textContent = "Error";
    kpiTrendEl.textContent = "N/A";
  }
}
// --- ▲▲▲ FIN NUEVA FUNCIÓN ▲▲▲ ---


// --- ▼▼▼ LÓGICA DEL MODAL DE GRÁFICO (EXISTENTE) ▼▼▼ ---
async function loadSalesChartData(sucursalId = 'all') {
    console.log(`Cargando DATOS DE GRÁFICO para sucursal: ${sucursalId}`);
    const ctx = document.getElementById('salesChartModalCanvas')?.getContext('2d');
    if (salesChart) {
        salesChart.destroy(); 
    }
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
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Error del servidor");
        }
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
    if (!ctx || !currentChartData) {
        console.warn("No hay contexto de canvas o datos para renderizar.");
        return;
    }

    currentChartType = type; 
    
    $all('.chart-type-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.type === type);
    });

    if (salesChart) {
        salesChart.destroy();
    }

    let specificConfig = {};
    const datasets = JSON.parse(JSON.stringify(currentChartData.datasets)); 

    if (type === 'line') {
        specificConfig = {
            type: 'line',
            data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: false})) }
        };
    } 
    else if (type === 'radar') {
        specificConfig = {
            type: 'radar',
            data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: true})) }
        };
    }
    else if (type === 'bar-stacked') {
        specificConfig = {
            type: 'bar',
            data: { ...currentChartData, datasets },
            options: { scales: { x: { stacked: true }, y: { stacked: true } } }
        };
    }
    else if (type === 'line-filled') {
        specificConfig = {
            type: 'line',
            data: { ...currentChartData, datasets: datasets.map(ds => ({...ds, fill: true})) }
        };
    }
    else { // 'bar' (agrupado) es el default
        specificConfig = {
            type: 'bar',
            data: { ...currentChartData, datasets }
        };
    }

    const baseConfig = {
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Ventas Mensuales (Año Actual vs. Año Pasado)',
                    font: { size: 16 }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += formatCLP(context.parsed.y);
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 10000000, 
                    ticks: {
                        stepSize: 1000000, 
                        callback: function(value, index, values) {
                            if (value === 0) return '0';
                            return `${value / 1000000}M`; 
                        }
                    }
                }
            },
            ...specificConfig.options
        }
    };

    salesChart = new Chart(ctx, {
        type: specificConfig.type,
        data: specificConfig.data,
        options: baseConfig.options
    });
}

function openSalesChartModal() {
    const modal = $('#sales-chart-modal');
    if (!modal) return;
    modal.classList.add('visible');
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadSalesChartData(sucursalId);
}

function closeSalesChartModal() {
    const modal = $('#sales-chart-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    if (salesChart) {
        salesChart.destroy();
        salesChart = null;
        currentChartData = null;
    }
}
// --- ▲▲▲ FIN LÓGICA MODAL GRÁFICO ▲▲▲ ---


// --- ▼▼▼ NUEVA LÓGICA PARA MODALES DE PEDIDOS ▼▼▼ ---

/**
 * Abre el Modal 1 (Lista de Pedidos) y carga los datos.
 */
function openPedidosListModal() {
    const modal = $('#pedidos-list-modal');
    if (!modal) return;
    
    modal.classList.add('visible');
    
    const sucursalId = $("#admin-sucursal-selector")?.value || 'all';
    loadPedidosListData(sucursalId);
}

/**
 * Cierra el Modal 1 (Lista de Pedidos).
 */
function closePedidosListModal() {
    const modal = $('#pedidos-list-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    // Limpia la tabla al cerrar
    const tbody = $('#pedidos-modal-tbody');
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';
    }
}

/**
 * Carga los datos de la lista de pedidos (Modal 1).
 */
async function loadPedidosListData(sucursalId = 'all') {
    const tbody = $('#pedidos-modal-tbody');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="3" class="no-data">Cargando...</td></tr>';

    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/lista_pedidos_mes?sucursal_id=${sucursalId}`, {
            credentials: "include"
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Error del servidor");
        }
        const pedidos = await response.json();

        if (pedidos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="no-data">No se encontraron pedidos este mes.</td></tr>';
            return;
        }

        // Poblar la tabla
        let html = '';
        pedidos.forEach(pedido => {
            const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''}`.trim();
            html += `
                <tr>
                    <td>#${pedido.id_pedido}</td>
                    <td>
                                                <a href="#" class="pedido-detail-link" data-id-pedido="${pedido.id_pedido}">
                          ${nombreCompleto}
                        </a>
                    </td>
                    <td>${pedido.total_items || 0}</td>
                </tr>
            `;
        });
        tbody.innerHTML = html;

    } catch (error) {
        console.error("Error cargando lista de pedidos:", error);
        tbody.innerHTML = `<tr><td colspan="3" class="no-data" style="color: red;">Error al cargar: ${error.message}</td></tr>`;
    }
}


/**
 * Abre el Modal 2 (Detalle del Pedido) y carga los datos.
 */
function openPedidosDetailModal(id_pedido) {
    const modal = $('#pedidos-detail-modal');
    if (!modal) return;
    
    modal.classList.add('visible');
    loadPedidoDetailData(id_pedido);
}

/**
 * Cierra el Modal 2 (Detalle del Pedido).
 */
function closePedidosDetailModal() {
    const modal = $('#pedidos-detail-modal');
    if (modal) {
        modal.classList.remove('visible');
    }
    // Limpia los campos al cerrar
    $all('#pedidos-detail-modal span[id^="detalle-"]').forEach(span => {
        span.textContent = '...';
    });
    const tbody = $('#detalle-items-tbody');
    if (tbody) {
        tbody.innerHTML = '';
    }
}

/**
 * Carga los datos de un pedido específico (Modal 2).
 */
async function loadPedidoDetailData(id_pedido) {
    try {
        const response = await fetch(`${API_BACKEND}/api/admin/reportes/detalle_pedido/${id_pedido}`, {
            credentials: "include"
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || "Error del servidor");
        }
        const data = await response.json();
        const pedido = data.pedido;
        const items = data.items;

        // --- Poblar Datos del Cliente ---
        const nombreCompleto = `${pedido.nombre_usuario || ''} ${pedido.apellido_paterno || ''} ${pedido.apellido_materno || ''}`.trim();
        const direccionCompleta = `${pedido.calle || ''} ${pedido.numero_calle || ''}`.trim();
        
        $('#detalle-cliente-nombre').textContent = nombreCompleto;
        $('#detalle-cliente-email').textContent = pedido.email_usuario || 'N/A';
        $('#detalle-cliente-telefono').textContent = pedido.telefono || 'N/A';
        $('#detalle-cliente-direccion').textContent = direccionCompleta || 'N/A';
        $('#detalle-cliente-comuna').textContent = pedido.comuna || 'N/A';
        $('#detalle-cliente-ciudad').textContent = pedido.ciudad || 'N/A';
        $('#detalle-cliente-region').textContent = pedido.region || 'N/A';

        // --- Poblar Datos del Pedido ---
        $('#detalle-pedido-id').textContent = pedido.id_pedido;
        $('#detalle-pedido-id-2').textContent = pedido.id_pedido;
        $('#detalle-pedido-fecha').textContent = formatFecha(pedido.creado_en);
        $('#detalle-pedido-total').textContent = formatCLP(pedido.total);
        $('#detalle-pedido-metodo').textContent = pedido.metodo_pago || 'N/A';
        $('#detalle-pedido-estado').textContent = pedido.estado_pedido || 'N/A';
        $('#detalle-pedido-transaccion').textContent = pedido.transaccion_id || 'N/A';

        // --- Poblar Tabla de Items ---
        const itemsTbody = $('#detalle-items-tbody');
        let itemsHtml = '';
        if (items.length > 0) {
            items.forEach(item => {
                itemsHtml += `
                    <tr>
                        <td>${item.nombre_producto || 'Producto no encontrado'}</td>
                        <td>${item.sku_producto || 'N/A'}</td>
                        <td>${item.talla || 'Única'}</td>
                        <td>${item.color || 'N/A'}</td>
                        <td>${item.cantidad}</td>
                        <td>${formatCLP(item.precio_unitario)}</td>
                    </tr>
                `;
            });
        } else {
            itemsHtml = '<tr><td colspan="6" class="no-data">No se encontraron items para este pedido.</td></tr>';
        }
        itemsTbody.innerHTML = itemsHtml;

    } catch (error) {
        console.error(`Error cargando detalle del pedido ${id_pedido}:`, error);
        // Opcional: mostrar error en el modal
        $('#detalle-cliente-nombre').textContent = `Error: ${error.message}`;
    }
}

// --- ▲▲▲ FIN NUEVA LÓGICA DE MODALES ▲▲▲ ---


// --- Evento Principal (MODIFICADO) ---
document.addEventListener("DOMContentLoaded", () => {
  // Selectores existentes
  const selectorSucursal = $("#admin-sucursal-selector");
  const kpiVentasCard = $("#kpi-ventas-card");
  const modalCloseBtn = $("#modal-close-btn");
  const modalOverlay = $("#sales-chart-modal");
  const chartTypeButtons = $all('.chart-type-btn');
  const sidebarToggle = $("#sidebarToggle");
  const sidebar = $("#adminSidebar");
  
  // --- ▼▼▼ NUEVOS Selectores para Pedidos ▼▼▼ ---
  const kpiPedidosCard = $("#kpi-pedidos-card");
  const pedidosListModal = $("#pedidos-list-modal");
  const pedidosListCloseBtn = $("#pedidos-list-close-btn");
  const pedidosListBody = $("#pedidos-modal-tbody");
  const pedidosDetailModal = $("#pedidos-detail-modal");
  const pedidosDetailCloseBtn = $("#pedidos-detail-close-btn");
  // --- ▲▲▲ FIN NUEVOS Selectores ▲▲▲ ---


  // 1. Cargar el selector de sucursales
  cargarSucursales();

  // 2. Cargar los KPIs iniciales (para "Todas las sucursales")
  cargarKPIVentas('all');
  cargarKPIPedidos('all'); // <-- NUEVA LLAMADA
  
  // 3. Listener para el selector de sucursal
  if (selectorSucursal) {
    selectorSucursal.addEventListener("change", () => {
      const sucursalIdSeleccionada = selectorSucursal.value;
      
      // Recargar KPIs
      cargarKPIVentas(sucursalIdSeleccionada);
      cargarKPIPedidos(sucursalIdSeleccionada); // <-- NUEVA LLAMADA
      
      // Recargar datos del gráfico si el modal está abierto
      if (modalOverlay && modalOverlay.classList.contains('visible')) {
          loadSalesChartData(sucursalIdSeleccionada);
      }
      
      // (NUEVO) Recargar lista de pedidos si el modal está abierto
      if (pedidosListModal && pedidosListModal.classList.contains('visible')) {
          loadPedidosListData(sucursalIdSeleccionada);
      }
    });
  }
  
  // 4. Listeners para el Modal de Ventas (Gráfico)
  if (kpiVentasCard) {
      kpiVentasCard.addEventListener('click', openSalesChartModal);
  }
  if (modalCloseBtn) {
      modalCloseBtn.addEventListener('click', closeSalesChartModal);
  }
  if (modalOverlay) {
      modalOverlay.addEventListener('click', (e) => {
          if (e.target === modalOverlay) { 
              closeSalesChartModal();
          }
      });
  }
  
  // 5. Listeners para los botones de tipo de gráfico
  chartTypeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
          const type = btn.dataset.type;
          renderSalesChart(type);
      });
  });

  // --- ▼▼▼ NUEVOS Listeners para Modales de Pedidos ▼▼▼ ---
  
  // Abrir Modal 1 (Lista)
  if (kpiPedidosCard) {
      kpiPedidosCard.addEventListener('click', openPedidosListModal);
  }
  
  // Cerrar Modal 1 (Lista)
  if (pedidosListCloseBtn) {
      pedidosListCloseBtn.addEventListener('click', closePedidosListModal);
  }
  if (pedidosListModal) {
      pedidosListModal.addEventListener('click', (e) => {
          if (e.target === pedidosListModal) { // Cierra si se hace clic en el fondo
              closePedidosListModal();
          }
      });
  }
  
  // Cerrar Modal 2 (Detalle)
  if (pedidosDetailCloseBtn) {
      pedidosDetailCloseBtn.addEventListener('click', closePedidosDetailModal);
  }
  if (pedidosDetailModal) {
      pedidosDetailModal.addEventListener('click', (e) => {
          if (e.target === pedidosDetailModal) { // Cierra si se hace clic en el fondo
              closePedidosDetailModal();
          }
      });
  }
  
  // Listener de clic delegado en la tabla del Modal 1
  if (pedidosListBody) {
      pedidosListBody.addEventListener('click', (e) => {
          // Busca el enlace (o su padre) que tenga la clase
          const link = e.target.closest('.pedido-detail-link');
          if (link) {
              e.preventDefault(); // Evita que el enlace '#' navegue
              const idPedido = link.dataset.idPedido;
              if (idPedido) {
                  openPedidosDetailModal(idPedido);
              }
          }
      });
  }
  // --- ▲▲▲ FIN NUEVOS Listeners ▲▲▲ ---


  // Lógica del sidebar (existente)
  if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener("click", () => {
          sidebar.classList.toggle("collapsed");
      });
  }
});