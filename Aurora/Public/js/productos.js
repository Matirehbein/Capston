// ../Public/js/productos.js

const API_BASE = "http://127.0.0.1:5000"; // ajusta si usas otra IP
const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

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

function renderRows(items) {
  const tbody = $("#productsTable tbody");
  tbody.innerHTML = "";
  for (const p of items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><input type="checkbox" class="row-check" data-id="${p.id_producto}"></td>
      <td>${p.sku || ""}</td>
      <td>${p.nombre_producto || ""}</td>
      <td>${p.categoria_producto || ""}</td>
      <td>${p.stock ?? 0}</td>
      <td>$${Number(p.precio_producto || 0).toLocaleString("es-CL")}</td>
    `;
    tbody.appendChild(tr);
  }
}

async function loadTable() {
  const q = ($("#searchInput")?.value || "").trim();
  const pill = $(".pill.active");
  const cat = pill?.dataset?.cat || "todas";
  const url = new URL(`${API_BASE}/api/productos`);
  if (q) url.searchParams.set("q", q);
  if (cat && cat.toLowerCase() !== "todas") url.searchParams.set("categoria", cat);

  const data = await fetchJSON(url.toString());
  renderRows(data);
}

function bindFilters() {
  // Búsqueda
  $("#searchInput")?.addEventListener("input", debounce(loadTable, 250));

  // Filtros de categoría
  $$(".pill").forEach(btn => {
    btn.addEventListener("click", () => {
      $$(".pill").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      loadTable();
    });
  });
}

function bindSelectAll() {
  const selectAll = $("#selectAllProd");
  selectAll?.addEventListener("change", () => {
    $$(".row-check").forEach(chk => chk.checked = selectAll.checked);
  });
}

function openModal() {
  $("#newProdModal")?.classList.add("show");
}
function closeModal() {
  $("#newProdModal")?.classList.remove("show");
  $("#newProdForm")?.reset();
}

function bindModal() {
  $("#newProdBtn")?.addEventListener("click", openModal);
  $("#closeNewProd")?.addEventListener("click", closeModal);
  $("#cancelNewProd")?.addEventListener("click", closeModal);

  $("#newProdForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const sku = $("#pSku").value.trim();
    const nombre = $("#pNombre").value.trim();
    const categoria = $("#pCategoria").value.trim();
    const stock = $("#pStock").value.trim(); // si luego decides crear stock inicial, será otro endpoint
    const precio = $("#pPrecio").value.trim();
    const imagen = $("#pImagen").value.trim();

    if (!sku || !nombre || !precio) {
      alert("SKU, Nombre y Precio son obligatorios.");
      return;
    }

    try {
      await fetchJSON(`${API_BASE}/api/productos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku,
          nombre_producto: nombre,
          categoria_producto: categoria || null,
          precio_producto: Number(precio),
          imagen_url: imagen || null,
          descripcion_producto: null
        })
      });
      closeModal();
      await loadTable();
    } catch (err) {
      alert(err.message || "Error creando producto");
    }
  });
}

function bindBulkDelete() {
  $("#deleteProdBulk")?.addEventListener("click", async () => {
    const ids = $$(".row-check:checked").map(chk => Number(chk.dataset.id));
    if (!ids.length) {
      alert("Selecciona al menos un producto.");
      return;
    }
    if (!confirm(`¿Eliminar ${ids.length} producto(s)?`)) return;

    try {
      await fetchJSON(`${API_BASE}/api/productos/bulk_delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids })
      });
      await loadTable();
      $("#selectAllProd").checked = false;
    } catch (err) {
      alert(err.message || "Error al eliminar");
    }
  });
}

// Utilidad
function debounce(fn, wait) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(null, args), wait);
  };
}

// Init
document.addEventListener("DOMContentLoaded", async () => {
  bindFilters();
  bindModal();
  bindBulkDelete();

  await loadTable();
  bindSelectAll();
});
