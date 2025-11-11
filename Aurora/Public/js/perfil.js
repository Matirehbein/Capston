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

// ✅ MENÚ DE USUARIO (logout y desplegable)
function bindUserMenu() {
  const logoutBtn = $("#logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      try {
        await fetchJSON(`${API_BASE}/logout`, { method: "GET" });
        window.location.href = "/src/login.html";
      } catch (err) {
        console.error(err);
        alert("Error al cerrar sesión.");
      }
    });
  }
}

// ✅ Mostrar pedidos simples en tarjetas
function renderOrders(pedidos) {
  const listEl = $("#ordersList");
  const empty = $("#ordersEmpty");
  const count = $("#ordersCount");

  if (!pedidos || pedidos.length === 0) {
    listEl.innerHTML = "";
    empty.style.display = "block";
    empty.innerHTML = `
      <p>No tienes pedidos en estado pagado, enviado o entregado.</p>
      <a class="btn" href="/src/productos.html">Explorar productos</a>
    `;
    count.textContent = "";
    return;
  }

  empty.style.display = "none";
  listEl.innerHTML = "";
  count.textContent = `${pedidos.length} pedido(s)`;


  pedidos.forEach(p => {
    const card = document.createElement("div");
    card.className = "order-card";

    card.innerHTML = `
      <div class="order-header">
        <strong>Pedido #${p.id_pedido}</strong>
        <span>${new Date(p.fecha).toLocaleString("es-CL")}</span>
      </div>

      <div class="order-items">
        ${
          p.productos && p.productos.length > 0 
          ? p.productos.map(prod => `
            <div class="order-item">
              <img src="${prod.imagen_url || '/Public/imagenes/default.png'}" alt="${prod.nombre}" />
              <div>
                <p>${prod.nombre}</p>
                <small>
                  ${prod.cantidad} x ${formatCLP(prod.precio_unitario || 0)}
                  ${prod.talla && prod.talla !== "N/A" ? `<br>Talla: ${prod.talla}` : ""}
                </small>
              </div>
              <span class="subtotal">${formatCLP((prod.precio_unitario || 0) * prod.cantidad)}</span>
            </div>
          `).join("")
          : "<p class='muted'>No hay productos en este pedido</p>"
        }
      </div>

      <div class="order-footer">
        <span>Total: <strong>${formatCLP(p.total)}</strong></span>
        <span class="estado ${p.estado_pedido}">${p.estado_pedido}</span>
      </div>
    `;

    listEl.appendChild(card);
  });
}

// ✅ Cargar sesión y pedidos desde Flask
async function loadSessionAndOrders() {
  try {
    const session = await fetchJSON(`${API_BASE}/api/session_info`);

    // Si no está logueado → enviar al login
    if (!session.logged_in) {
      window.location.href = "/src/login.html";
      return;
    }

    // Mostrar nombre en el header (igual que main.html)
    const name = `${session.nombre || ''} ${session.apellido_paterno || ''}`.trim();
    const welcomeMsg = $("#welcome-msg");
    if (welcomeMsg) {
      welcomeMsg.textContent = `Hola, ${name}`;
      welcomeMsg.style.display = "inline";
    }

    // Mostrar botón admin si corresponde
    if (session.rol_usuario === "admin" || session.rol_usuario === "soporte") {
      const adminBtn = $("#admin-menu-btn");
      if (adminBtn) adminBtn.style.display = "inline";
    }

    // Cargar pedidos
    const pedidos = await fetchJSON(`${API_BASE}/api/mis_pedidos`);
    renderOrders(pedidos);

  } catch (err) {
    console.error("❌ Error cargando perfil o pedidos:", err);
  }
}

// ✅ Inicialización
document.addEventListener("DOMContentLoaded", async () => {
  bindUserMenu();
  await loadSessionAndOrders();
});
