// ===============================
// productos.js (ADMIN)
// ===============================

const API_BASE = "http://localhost:5000";
const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

// ===============================
// VARIABLES GLOBALES PARA EL MODAL
// ===============================
let MODAL_VARIACIONES = [];
let MODAL_STOCK = [];

// ===============================
// FETCH JSON
// ===============================
async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Accept": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    let msg = await res.text();
    try { const j = JSON.parse(msg); msg = j.error || msg; } catch {}
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return res.json();
}

// ===============================
// FORMATO CLP
// ===============================
function CLP(n) {
  return Number(n || 0).toLocaleString("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });
}

// ===============================
//  RENDER TABLA PRINCIPAL
// ===============================
function renderRows(items) {
  const tbody = $("#productsTable tbody");
  tbody.innerHTML = "";

  for (const p of items) {
    const tr = document.createElement("tr");
    tr.dataset.idProducto = p.id_producto;

    tr.innerHTML = `
      <td>${p.sku || ""}</td>
      <td>${p.nombre_producto || ""}</td>
      <td>${p.categoria_producto || ""}</td>
      <td>${p.stock ?? 0}</td>
      <td>${CLP(p.precio_producto)}</td>
    `;

    tbody.appendChild(tr);
  }
}

// ===============================
//  CARGAR PRODUCTOS
// ===============================
async function loadTable() {
  const q = ($("#searchInput")?.value || "").trim();
  const activePill = $(".pill.active");
  const categoria = activePill?.dataset?.cat || "todas";

  const url = new URL(`${API_BASE}/api/productos`);
  if (q) url.searchParams.set("q", q);
  if (categoria !== "todas") url.searchParams.set("categoria", categoria);

  const data = await fetchJSON(url.toString());
  renderRows(data);
}

// ===============================
//  FILTROS Y BUSQUEDA
// ===============================
function bindFilters() {
  $("#searchInput")?.addEventListener("input", debounce(loadTable, 250));

  $$(".pill").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      loadTable();
    });
  });
}

// ===============================
//  MODAL DETALLE DE PRODUCTO
// ===============================
function openProductoModal() {
  $("#producto-modal")?.classList.add("visible");
}

function closeProductoModal() {
  $("#producto-modal")?.classList.remove("visible");

  $("#modal-variaciones").innerHTML = "";
  $("#modal-stock-sucursales").innerHTML = "";
}

function bindModalClose() {
  $("#modal-close")?.addEventListener("click", closeProductoModal);

  $("#producto-modal")?.addEventListener("click", e => {
    if (e.target.id === "producto-modal") closeProductoModal();
  });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeProductoModal();
  });
}

// ===============================
//  FUNCIÓN PARA RENDERIZAR TABLAS SEGÚN FILTRO
// ===============================
function renderModalTables(filtroSucursal) {

  // -----------------------------
  // STOCK POR SUCURSAL
  // -----------------------------
  const stockBody = $("#modal-stock-sucursales");
  stockBody.innerHTML = "";

  const stockFiltrado = 
    filtroSucursal === "todas" 
      ? MODAL_STOCK
      : MODAL_STOCK.filter(s => s.sucursal === filtroSucursal);

  if (!stockFiltrado.length) {
    stockBody.innerHTML = `<tr><td colspan="4">Sin stock</td></tr>`;
  } else {
    stockFiltrado.forEach(s => {
      stockBody.innerHTML += `
        <tr>
          <td>${s.sucursal}</td>
          <td>${s.talla}</td>
          <td>${s.stock}</td>
        </tr>
      `;
    });
  }
}

// ===============================
//  CARGAR DETALLE DEL PRODUCTO
// ===============================
async function loadProductoDetalle(idProducto) {
  try {
    const url = `${API_BASE}/api/admin/productos/${idProducto}/detalle`;
    const data = await fetchJSON(url);

    const prod = data.producto || {};

    // Guardar datos globales
    MODAL_VARIACIONES = data.variaciones || [];
    MODAL_STOCK = data.stock_sucursales || [];

    // Datos principales
    $("#modal-producto-nombre").textContent = prod.nombre_producto || "Producto";
    $("#modal-sku").textContent = prod.sku || "—";
    $("#modal-categoria").textContent = prod.categoria_producto || "—";
    $("#modal-precio").textContent = CLP(prod.precio_producto || 0);
    $("#modal-descripcion").textContent = prod.descripcion_producto || "Sin descripción";
    $("#modal-producto-img").src = prod.imagen_url || "/Public/imagenes/default.png";

    // Variaciones
    let varHTML = "";
    MODAL_VARIACIONES.forEach(v => {
      varHTML += `
        <tr>
          <td>${v.talla || "—"}</td>
          <td>${v.color || "—"}</td>
          <td>${v.sku_variacion || "—"}</td>
        </tr>
      `;
    });
    $("#modal-variaciones").innerHTML = varHTML || `<tr><td colspan="3">Sin variaciones</td></tr>`;

    // Llenar selector de sucursales
    const sucSel = $("#modal-filtro-sucursal");
    sucSel.innerHTML = `<option value="todas">Todas las sucursales</option>`;

    const sucursalesUnicas = [...new Set(MODAL_STOCK.map(s => s.sucursal))];
    sucursalesUnicas.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sucSel.appendChild(opt);
    });

    // Render inicial sin filtro
    renderModalTables("todas");

    openProductoModal();

  } catch (err) {
    console.error("Error cargando detalle:", err);
    alert("Error cargando detalle del producto");
  }
}

// ===============================
//  CLICK EN FILA → ABRIR MODAL
// ===============================
function bindRowClick() {
  $("#productsTable tbody")?.addEventListener("click", e => {
    const tr = e.target.closest("tr[data-id-producto]");
    if (!tr) return;
    loadProductoDetalle(tr.dataset.idProducto);
  });
}

// ===============================
// UTILIDAD: DEBOUNCE
// ===============================
function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(null, args), wait);
  };
}

// ===============================
// INIT
// ===============================
document.addEventListener("DOMContentLoaded", async () => {
  bindFilters();
  bindModalClose();
  bindRowClick();

  // Evento del filtro de sucursal
  $("#modal-filtro-sucursal")?.addEventListener("change", e => {
    renderModalTables(e.target.value);
  });

  await loadTable();
});
