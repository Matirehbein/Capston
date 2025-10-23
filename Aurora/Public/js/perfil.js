const API_BASE = "http://localhost:5000";
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

function formatCLP(v) {
  try {
    return Number(v).toLocaleString("es-CL", { 
      style: "currency", 
      currency: "CLP", 
      maximumFractionDigits: 0 
    });
  } catch { 
    return `$${v}`; 
  }
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

// === MENÚ DE CUENTA (abre/cierra y logout) ===
function bindAccountMenu() {
  const btn = $("#accountBtn");
  const menu = $("#accountMenu");
  if (!btn || !menu) return;

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    menu.classList.toggle("show");
  });

  document.addEventListener("click", (e) => {
    if (!menu.contains(e.target) && !btn.contains(e.target)) {
      menu.classList.remove("show");
    }
  });

  // Cerrar sesión
  $("#logoutBtn")?.addEventListener("click", async () => {
    try {
      await fetchJSON(`${API_BASE}/logout`, { method: "GET" });
      window.location.href = "/src/login.html";
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

// === RENDERIZA PEDIDOS ===
function renderOrders(list) {
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

  // Limpia filas anteriores (dejando cabecera)
  listEl.querySelectorAll(".order-row:not(.order-head)").forEach(n => n.remove());

  for (const o of list) {
    const row = document.createElement("div");
    row.className = "order-row";
    row.innerHTML = `
      <div>${o.id_pedido}</div>
      <div>${new Date(o.fecha_pedido || o.creado_en).toLocaleString("es-CL")}</div>
      <div>${formatCLP(o.total)}</div>
      <div>${estadoBadge(o.estado_pedido || o.estado)}</div>
      <div><a class="btn-sm" href="/src/pedido_detalle.html?id=${o.id_pedido}">Ver detalle</a></div>
    `;
    listEl.appendChild(row);
  }
  count.textContent = `${list.length} pedido(s)`;
}

// === CARGA SESSION + PEDIDOS ===
async function loadSessionAndOrders() {
  try {
    const session = await fetchJSON(`${API_BASE}/api/session_info`);

    // Si no hay sesión, redirigir a login
    if (!session.logged_in) {
      window.location.href = "/src/login.html";
      return;
    }

    // Mostrar nombre en la esquina del menú
    const name = [session.nombre, session.apellido_paterno].filter(Boolean).join(" ");
    const welcome = $("#welcomeUser");
    if (welcome) welcome.textContent = `Hola, ${name || session.email_usuario}`;

    // Mostrar botón admin si el rol lo permite
    if (session.rol_usuario === "admin" || session.rol_usuario === "soporte") {
      const adminBtn = $("#admin-menu-btn");
      if (adminBtn) adminBtn.style.display = "inline";
    }

    // Intentar cargar pedidos, pero sin romper la página si falla
    try {
      const orders = await fetchJSON(`${API_BASE}/api/mis_pedidos`);
      renderOrders(orders);
    } catch (pedidoError) {
      console.warn("⚠️ No se pudieron cargar los pedidos:", pedidoError.message);
      const emptyBox = $("#ordersEmpty");
      if (emptyBox) {
        emptyBox.style.display = "block";
        emptyBox.innerHTML = `
          <p>No pudimos cargar tus pedidos en este momento.</p>
          <a class="btn" href="/src/productos.html">Explorar productos</a>
        `;
      }
    }

  } catch (err) {
    console.error("❌ Error cargando perfil o sesión:", err);
    alert("Tu sesión no está activa. Por favor inicia sesión nuevamente.");
    window.location.href = "/src/login.html";
  }
}

// === INICIALIZACIÓN ===
document.addEventListener("DOMContentLoaded", async () => {
  bindAccountMenu();
  await loadSessionAndOrders();
});

