// ../Public/js/clientes.js

// ==== Helpers ====
const $ = (s, r = document) => r.querySelector(s);
const $all = (s, r = document) => r.querySelectorAll(s);

const API_BACKEND = "http://localhost:5000";
console.log("[clientes.js] cargado");

function formatFecha(fechaStr) {
  if (!fechaStr) return "—";
  const d = new Date(fechaStr);
  if (isNaN(d.getTime())) return fechaStr;
  return d.toLocaleString("es-CL", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getInitials(nombreCompleto = "") {
  const clean = nombreCompleto.trim();
  if (!clean) return "CL";
  const parts = clean.split(/\s+/);
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function formatCLP(n) {
  const num = Number(n) || 0;
  return num.toLocaleString("es-CL", {
    style: "currency",
    currency: "CLP",
    maximumFractionDigits: 0,
  });
}

let clientesCache = [];

// ==========================================================
// =============== Cargar lista de clientes =================
// ==========================================================

async function loadClientesPage() {
  const tbody = $("#clientes-page-tbody");
  const thead = $("#clientes-page-thead");
  const sucursalSelector = $("#admin-sucursal-selector");

  if (!tbody || !thead) return;

  const sucursalId = sucursalSelector?.value || "all";
  const esTodas = sucursalId === "all";

  thead.innerHTML = esTodas
    ? `<tr><th>Nombre Cliente</th><th>Email</th><th>Fecha Registro</th></tr>`
    : `<tr><th>Nombre Cliente</th><th>Email</th><th>Dirección</th></tr>`;

  tbody.innerHTML = `<tr><td colspan="3" class="no-data">Cargando clientes...</td></tr>`;

  try {
    const url = `${API_BACKEND}/api/admin/reportes/lista_nuevos_clientes?sucursal_id=${encodeURIComponent(
      sucursalId
    )}`;

    console.log("[clientes.js] Fetch:", url);

    const res = await fetch(url, { credentials: "include" });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const clientes = await res.json();
    clientesCache = Array.isArray(clientes) ? clientes : [];

    if (!clientesCache.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="no-data">No se encontraron clientes.</td></tr>`;
      return;
    }

    renderClientesTable(esTodas);
  } catch (err) {
    console.error("[clientes.js] Error cargando clientes:", err);
    tbody.innerHTML = `<tr><td colspan="3" class="no-data" style="color:red;">Error al cargar clientes.</td></tr>`;
  }
}

// ==========================================================
// ====================== Render tabla ======================
// ==========================================================

function renderClientesTable(esTodas) {
  const tbody = $("#clientes-page-tbody");
  const searchInput = $("#clientes-search");

  if (!tbody) return;

  const q = (searchInput?.value || "").toLowerCase().trim();

  const lista = clientesCache.filter((cliente) => {
    const nombreCompleto = `${cliente.nombre_usuario || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`.trim().toLowerCase();

    const email = (cliente.email_usuario || "").toLowerCase();

    if (!q) return true;
    return nombreCompleto.includes(q) || email.includes(q);
  });

  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="no-data">No se encontraron resultados.</td></tr>`;
    return;
  }

  let html = "";

  lista.forEach((cliente) => {
    const nombreCompleto = `${cliente.nombre_usuario || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`.trim();

    const email = cliente.email_usuario || "(Sin correo)";
    const initials = getInitials(nombreCompleto || email);

    html += `<tr data-id-cliente="${cliente.id_usuario}">`;

    html += `
      <td class="cliente-cell">
        <div class="avatar-sm">${initials}</div>
        <div class="cliente-texts">
          <span class="cliente-nombre">${nombreCompleto}</span>
          <span class="cliente-email">${email}</span>
        </div>
      </td>
    `;

    html += `<td>${email}</td>`;

    if (esTodas) {
      html += `<td>${formatFecha(cliente.creado_en)}</td>`;
    } else {
      const direccion = `${cliente.region || ""}, ${cliente.ciudad || ""}, ${
        cliente.comuna || ""
      }, ${cliente.calle || ""} ${cliente.numero_calle || ""}`
        .replace(/, ,/g, ",")
        .replace(/^, | ,$/g, "")
        .trim();

      html += `<td>${direccion || "(Sin dirección)"}</td>`;
    }

    html += `</tr>`;
  });

  tbody.innerHTML = html;
}

// ==========================================================
// ==================== MODAL CLIENTE =======================
// ==========================================================

function openClienteDetailModal(idCliente) {
  const overlay = $("#clientes-detail-modal");
  if (!overlay) return;
  overlay.classList.add("visible");
  loadClienteDetailData(idCliente);
}

function closeClienteDetailModal() {
  const overlay = $("#clientes-detail-modal");
  if (!overlay) return;
  overlay.classList.remove("visible");

  $all('#clientes-detail-modal span[id^="detalle-cliente-"]').forEach(
    (s) => (s.textContent = "...")
  );

  $("#cliente-pedidos-tbody").innerHTML = "";
}

// ==========================================================
// ============== Cargar historial del cliente ==============
// ==========================================================

async function loadClienteDetailData(idCliente) {
  const sucursalId = $("#admin-sucursal-selector")?.value || "all";

  const pedidosBody = $("#cliente-pedidos-tbody");
  pedidosBody.innerHTML =
    '<tr><td colspan="6" class="no-data">Cargando...</td></tr>';

  try {
    const url = `${API_BACKEND}/api/admin/reportes/historial_cliente/${idCliente}?sucursal_id=${encodeURIComponent(
      sucursalId
    )}`;

    console.log("[clientes.js] Historial cliente:", url);

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    const usuario = data.usuario || {};
    const pedidos = data.pedidos || [];

    const nombreCompleto = `${usuario.nombre_usuario || ""} ${
      usuario.apellido_paterno || ""
    } ${usuario.apellido_materno || ""}`.trim();

    const direccion = `${usuario.calle || ""} ${usuario.numero_calle || ""}`.trim();

    $("#detalle-cliente-nombre-modal").textContent = nombreCompleto;
    $("#detalle-cliente-nombre-2").textContent = nombreCompleto;
    $("#detalle-cliente-email-2").textContent = usuario.email_usuario || "N/A";
    $("#detalle-cliente-direccion-2").textContent = direccion || "N/A";
    $("#detalle-cliente-total-pedidos").textContent =
      pedidos.length || data.total_pedidos || 0;

    if (!pedidos.length) {
      pedidosBody.innerHTML =
        '<tr><td colspan="6" class="no-data">El cliente no tiene pedidos.</td></tr>';
      return;
    }

    let html = "";

    pedidos.forEach((p) => {
      html += `
        <tr>
          <td>#${p.id_pedido}</td>
          <td>${formatFecha(p.creado_en)}</td>
          <td>${p.nombre_sucursal || "N/A"}</td>

          <td style="max-width:220px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" 
              title="${p.productos_preview || ""}">
            ${p.productos_preview || "N/A"}
          </td>

          <td>${formatCLP(p.total)}</td>

          <td>
            <a href="#" class="pedido-detail-link" data-id-pedido="${p.id_pedido}">
              Ver
            </a>
          </td>
        </tr>`;
    });

    pedidosBody.innerHTML = html;
  } catch (err) {
    console.error("[clientes.js] Error:", err);
    pedidosBody.innerHTML =
      '<tr><td colspan="6" class="no-data" style="color:red;">Error al cargar historial.</td></tr>';
  }
}

// ==========================================================
// ============ MODAL DETALLE DEL PEDIDO ====================
// ==========================================================

function openClientePedidoDetailModal(idPedido) {
  const modal = $("#cliente-pedido-detail-modal");
  if (!modal) return;
  modal.classList.add("visible");
  loadClientePedidoDetailData(idPedido);
}

function closeClientePedidoDetailModal() {
  const modal = $("#cliente-pedido-detail-modal");
  if (!modal) return;

  modal.classList.remove("visible");

  
  [
    "cliente-detalle-pedido-id",
    "cliente-detalle-pedido-id-2",
    "cliente-detalle-pedido-fecha",
    "cliente-detalle-pedido-total",
    "cliente-detalle-pedido-metodo",
    "cliente-detalle-pedido-estado",
    "cliente-detalle-pedido-transaccion",
  ].forEach((id) => {
    const el = $(`#${id}`);
    if (el) el.textContent = "...";
  });

  const itemsBody = $("#cliente-detalle-items-tbody");
  if (itemsBody) itemsBody.innerHTML = "";
}


// =========== Cargar detalle del pedido ===========
async function loadClientePedidoDetailData(idPedido) {
  const sucursalId = $("#admin-sucursal-selector")?.value || "all";
  const itemsBody = $("#cliente-detalle-items-tbody");

  if (itemsBody) {
    itemsBody.innerHTML =
      '<tr><td colspan="7" class="no-data">Cargando items...</td></tr>';
  }

  try {
    const url = `${API_BACKEND}/api/admin/reportes/detalle_pedido/${idPedido}?sucursal_id=${encodeURIComponent(
      sucursalId
    )}`;
    console.log("[clientes.js] Detalle pedido:", url);

    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    const pedido = data.pedido || {};
    const items = Array.isArray(data.items) ? data.items : [];

    //  Datos del pedido
    $("#cliente-detalle-pedido-id").textContent = pedido.id_pedido || idPedido;
    $("#cliente-detalle-pedido-id-2").textContent =
      pedido.id_pedido || idPedido;
    $("#cliente-detalle-pedido-fecha").textContent = formatFecha(
      pedido.creado_en
    );
    $("#cliente-detalle-pedido-total").textContent = formatCLP(
      pedido.total || pedido.total_pagado
    );
    $("#cliente-detalle-pedido-metodo").textContent =
      pedido.metodo_pago || "N/A";
    $("#cliente-detalle-pedido-estado").textContent =
      pedido.estado_pago || pedido.estado_pedido || "N/A";
    $("#cliente-detalle-pedido-transaccion").textContent =
      pedido.id_transaccion || pedido.transaction_id || "N/A";

    //  Items comprados
    if (!items.length) {
      if (itemsBody) {
        itemsBody.innerHTML =
          '<tr><td colspan="7" class="no-data">Este pedido no tiene items registrados.</td></tr>';
      }
      return;
    }

    let html = "";
    items.forEach((it) => {
      const foto =
        it.foto_url ||
        it.foto_producto ||
        it.imagen_url ||
        it.url_imagen ||
        it.url_foto ||
        "";

      html += `
        <tr>
          <td>${
            foto
              ? `<img src="${foto}" class="item-foto" alt="producto" />`
              : "-"
          }</td>
          <td>${it.nombre_producto || it.nombre || "Producto"}</td>
          <td>${it.sku || it.sku_producto || "—"}</td>
          <td>${it.talla || "—"}</td>
          <td>${it.color || "—"}</td>
          <td>${it.cantidad || 0}</td>
          <td>${formatCLP(it.precio_unitario || it.precio || 0)}</td>
        </tr>`;
    });

    if (itemsBody) itemsBody.innerHTML = html;
  } catch (err) {
    console.error("[clientes.js] Error detalle pedido:", err);
    if (itemsBody) {
      itemsBody.innerHTML = `
        <tr>
          <td colspan="7" class="no-data" style="color:red;">
            Error al cargar el detalle del pedido.
          </td>
        </tr>`;
    }
  }
}


// ==========================================================
// ===================== EVENTOS ============================
// ==========================================================

document.addEventListener("DOMContentLoaded", () => {
  console.log("[clientes.js] DOMContentLoaded");

  loadClientesPage();

  $("#admin-sucursal-selector")?.addEventListener("change", loadClientesPage);

  $("#clientes-search")?.addEventListener("input", () => {
    const esTodas = ($("#admin-sucursal-selector")?.value || "all") === "all";
    renderClientesTable(esTodas);
  });

  // Click en fila del cliente
  $("#clientes-page-tbody")?.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-id-cliente]");
    if (!tr) return;
    openClienteDetailModal(tr.dataset.idCliente);
  });

  // Click en botón VER dentro del historial
  $("#cliente-pedidos-tbody")?.addEventListener("click", (e) => {
    const a = e.target.closest(".pedido-detail-link");
    if (!a) return;
    const idPedido = a.dataset.idPedido;
    openClientePedidoDetailModal(idPedido);
  });

  // Cerrar modals
  $("#clientes-detail-close-btn")?.addEventListener(
    "click",
    closeClienteDetailModal
  );
  $("#cliente-pedido-detail-close-btn")?.addEventListener(
    "click",
    closeClientePedidoDetailModal
  );

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeClienteDetailModal();
      closeClientePedidoDetailModal();
    }
  });
});
