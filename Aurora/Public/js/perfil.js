// /Public/js/perfil.js
const API_BASE = "http://localhost:5000";

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

function formatCLP(v) {
  try {
    return Number(v).toLocaleString("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
  } catch { return `$${v}`; }
}

async function fetchJSON(url, opts = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: { "Accept": "application/json", ...(opts.headers || {}) },
    ...opts
  });
  if (!res.ok) {
    let txt = await res.text();
    try { const j = JSON.parse(txt); txt = j.error || txt; } catch {}
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

// Toggle mini menú
function bindAccountMenu() {
  const btn = $("#accountBtn");
  const menu = $("#accountMenu");

  if (!btn || !menu) return;

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    menu.classList.toggle("show");
  });

  // Cerrar si se hace click fuera
  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && !btn.contains(e.target)) {
      menu.classList.remove("show");
    }
  });

  // Cerrar sesión
  $("#logoutBtn")?.addEventListener("click", async () => {
    try {
      await fetchJSON(`${API_BASE}/api/logout`, { method: "POST" });
      // Vuelve a la portada del frontend
      window.location.href = "/src/main.html";
    } catch (err) {
      console.error(err);
      alert("No se pudo cerrar sesión.");
    }
  });
}

function estadoBadge(estado) {
  const s = (estado || "").toString().toLowerCase();
  const cls = s.includes("pend") ? "pendiente" :
              s.includes("proc") ? "procesando" :
              s.includes("env")  ? "enviado" :
              s.includes("entr") ? "entregado" : "pendiente";
  return `<span class="badge ${cls}">${estado || "Pendiente"}</span>`;
}

function renderOrders(list) {
  const box = $("#ordersBox");
  const listEl = $("#ordersList");
  const empty = $("#ordersEmpty");
  const count = $("#ordersCount");

  if (!Array.isArray(list) || list.length === 0) {
    listEl.style.display = "none";
    empty.style.display = "block";
    count.textContent = "";
    return;
  }

  empty.style.display = "none";
  listEl.style.display = "block";

  // limpiamos filas previas (dejando el head)
  listEl.querySelectorAll(".order-row:not(.order-head)").forEach(n => n.remove());

  for (const o of list) {
    const row = document.createElement("div");
    row.className = "order-row";
    row.innerHTML = `
      <div>${o.id_pedido}</div>
      <div>${new Date(o.fecha_pedido || o.fecha || o.creado_en).toLocaleString("es-CL")}</div>
      <div>${formatCLP(o.total)}</div>
      <div>${estadoBadge(o.estado)}</div>
      <div><a class="btn-sm" href="/src/pedido_detalle.html?id=${o.id_pedido}">Ver detalle</a></div>
    `;
    listEl.appendChild(row);
  }
  count.textContent = `${list.length} pedido(s)`;
}

async function loadSessionAndOrders() {
  const session = await fetchJSON(`${API_BASE}/api/session_info`);
  if (!session.logged_in) {
    window.location.href = "/src/login.html";
    return;
  }

  // Bienvenida
  const name = [session.nombre, session.apellido_paterno].filter(Boolean).join(" ");
  const welcome = $("#welcomeUser");
  if (welcome) welcome.textContent = `Hola, ${name || session.email}`;

  // Mostrar menú admin si rol lo permite
  if (session.rol === "admin" || session.rol === "soporte") {
    const adminBtn = $("#admin-menu-btn");
    if (adminBtn) adminBtn.style.display = "inline";
  }

  // Cargar pedidos
  const orders = await fetchJSON(`${API_BASE}/api/mis_pedidos`);
  renderOrders(orders);
}

document.addEventListener("DOMContentLoaded", async () => {
  bindAccountMenu();
  try {
    await loadSessionAndOrders();
  } catch (err) {
    console.error(err);
    alert("No pudimos cargar tu perfil o pedidos.");
  }
});
