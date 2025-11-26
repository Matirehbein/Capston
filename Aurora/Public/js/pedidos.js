// =========================================
// pedidos.js (ADMIN)
// =========================================

const API_BASE = "http://localhost:5000";
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

// =========================================
// UTILIDAD FETCH JSON
// =========================================
async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: { Accept: "application/json" },
    ...opts,
  });

  if (!res.ok) {
    let msg = await res.text();
    try {
      const j = JSON.parse(msg);
      msg = j.error || msg;
    } catch {}
    throw new Error(msg || `HTTP ${res.status}`);
  }

  return res.json();
}

// =========================================
// FORMATO CLP
// =========================================
function CLP(n) {
  return Number(n || 0).toLocaleString("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });
}

// =========================================
// RENDER DE TABLA DE PEDIDOS
// =========================================
function renderOrders(pedidos) {
  const tbody = $("#ordersTable tbody");
  tbody.innerHTML = "";

  pedidos.forEach((p) => {
    const tr = document.createElement("tr");
    tr.dataset.status = (p.estado || "").toLowerCase();

    tr.innerHTML = `
      <td><input type="checkbox" class="row-check" data-id="${p.id_pedido}"></td>
      <td>${p.id_pedido}</td>
      <td>${p.cliente}</td>
      <td>${new Date(p.fecha).toLocaleDateString("es-CL")}</td>
      <td class="estado-cell">
        <div class="estado-wrap">
              <span class="badge ${p.estado?.toLowerCase() || "sin-estado"}">
              ${p.estado || "Sin estado"}
            </span>
        </div>
      </td>
      <td>${CLP(p.total)}</td>
      <td><button class="btn-sm alt view-btn" data-id="${p.id_pedido}">Ver</button></td>
    `;

    tbody.appendChild(tr);
  });
}

// =========================================
// CARGAR LISTA DE PEDIDOS
// =========================================
async function loadOrders() {
  const status = $(".pill.active")?.dataset.status || "todos";
  const q = $("#searchInput")?.value?.trim() || "";

  const url = new URL(`${API_BASE}/api/admin/pedidos`);
  if (status !== "todos") url.searchParams.set("status", status);
  if (q) url.searchParams.set("q", q);

  let data = await fetchJSON(url.toString());

  // ⛔ OCULTAR "pendiente" cuando estamos en "Todos"
  if (status === "todos") {
    data = data.filter(p => p.estado?.toLowerCase() !== "pendiente");
  }

  renderOrders(data);
}


// =========================================
// FILTROS (PILLS)
// =========================================
function bindFilters() {
  $$(".pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      loadOrders();
    });
  });
}

// =========================================
// BUSQUEDA
// =========================================
function bindSearch() {
  $("#searchInput")?.addEventListener("input", debounce(loadOrders, 250));
}

// Utilidad debounce
function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(null, args), wait);
  };
}

// =========================================
// SELECCIONAR TODOS CHECKBOXES
// =========================================
function bindSelectAll() {
  $("#selectAll").addEventListener("change", (e) => {
    const checked = e.target.checked;
    $$(".row-check").forEach((c) => (c.checked = checked));
  });
}

// =========================================
// CAMBIO MASIVO DE ESTADOS
// =========================================
async function applyBulkStatus() {
  const newStatus = $("#bulkStatus").value;
  if (!newStatus) return alert("Selecciona un estado válido");

  const ids = $$(".row-check")
    .filter((c) => c.checked)
    .map((c) => Number(c.dataset.id));

  if (!ids.length) return alert("No hay pedidos seleccionados");

  try {
    await fetchJSON(`${API_BASE}/api/admin/pedidos/bulk_estado`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids, estado: newStatus }),
    });

    alert("Estado actualizado correctamente");
    loadOrders();
  } catch (err) {
    alert("Error al actualizar: " + err.message);
  }
}

function bindBulkActions() {
  $("#applyBulk").addEventListener("click", applyBulkStatus);
}

// =========================================
// ABRIR MODAL DE DETALLE
// =========================================
function openModal() {
  $("#orderModal").classList.add("visible");
}

function closeModal() {
  $("#orderModal").classList.remove("visible");
}

// =========================================
// CARGAR DETALLE DE UN PEDIDO
// =========================================
async function loadOrderDetail(id) {
  try {
    const data = await fetchJSON(`${API_BASE}/api/admin/pedidos/${id}`);

    const ped = data.pedido;
    $("#modalTitle").textContent = `Pedido #${ped.id_pedido}`;
    $("#mCliente").textContent = ped.cliente;
    $("#mFecha").textContent = new Date(ped.fecha).toLocaleString("es-CL");
    $("#mEstado").textContent = ped.estado;
    $("#mTotal").textContent = CLP(ped.total);

    const ul = $("#mItems");
    ul.innerHTML = "";
    data.items.forEach((it) => {
      ul.innerHTML += `
        <li>
          <strong>${it.producto}</strong>  
          (${it.talla}, ${it.color}, SKU ${it.sku})  
          — ${it.cantidad} × ${CLP(it.precio_unitario)}
        </li>
      `;
    });

    openModal();
  } catch (err) {
    alert("Error cargando pedido: " + err.message);
  }
}

// =========================================
// CLICK "VER" EN FILA
// =========================================
function bindRowView() {
  $("#ordersTable tbody").addEventListener("click", (e) => {
    const btn = e.target.closest(".view-btn");
    if (!btn) return;
    const id = btn.dataset.id;
    loadOrderDetail(id);
  });
}

// =========================================
// CERRAR MODAL
// =========================================
function bindModalClose() {
  $("#closeModal").addEventListener("click", closeModal);

  // Cerrar cliqueando fuera de la tarjeta
  $("#orderModal").addEventListener("click", (e) => {
    if (e.target.id === "orderModal") closeModal();
  });
}

// =========================================
// INIT
// =========================================
document.addEventListener("DOMContentLoaded", async () => {
  bindFilters();
  bindSearch();
  bindSelectAll();
  bindBulkActions();
  bindModalClose();
  bindRowView();

  await loadOrders();
});
