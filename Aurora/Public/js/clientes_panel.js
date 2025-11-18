// ../Public/js/clientes.js

// Helpers
const $ = (s, r = document) => r.querySelector(s);
const $all = (s, r = document) => r.querySelectorAll(s);

// API_BACKEND ya lo usas en otros JS (reportes_admin.js).
// Si no existe, puedes poner directamente tu URL, por ejemplo:
const API_BACKEND = "http://localhost:5000";
console.log("[clientes.js] cargado");

// Formato de fecha igual que en reportes
function formatFecha(fechaStr) {
  if (!fechaStr) return "—";
  const d = new Date(fechaStr);
  if (isNaN(d.getTime())) return fechaStr; // por si ya viene formateada
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

let clientesCache = [];

// Cargar y pintar clientes en la tabla principal
async function loadClientesPage() {
  const tbody = $("#clientes-page-tbody");
  const thead = $("#clientes-page-thead");
  const sucursalSelector = $("#admin-sucursal-selector");

  if (!tbody || !thead) {
    console.error("[clientes.js] No se encontró thead/tbody de clientes");
    return;
  }

  const sucursalId = sucursalSelector?.value || "all";
  const esTodas = sucursalId === "all";

  // Encabezados (igual que en el modal)
  if (esTodas) {
    thead.innerHTML = `
      <tr>
        <th>Nombre Cliente</th>
        <th>Email</th>
        <th>Fecha Registro</th>
      </tr>`;
  } else {
    thead.innerHTML = `
      <tr>
        <th>Nombre Cliente</th>
        <th>Email</th>
        <th>Dirección</th>
      </tr>`;
  }

  tbody.innerHTML = `
    <tr>
      <td colspan="3" class="no-data">Cargando clientes...</td>
    </tr>`;

  try {
    const url = `${API_BACKEND}/api/admin/reportes/lista_nuevos_clientes?sucursal_id=${encodeURIComponent(
      sucursalId
    )}`;

    console.log("[clientes.js] Fetch:", url);

    const res = await fetch(url, { credentials: "include" });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const clientes = await res.json();
    console.log("[clientes.js] Clientes recibidos:", clientes);

    clientesCache = Array.isArray(clientes) ? clientes : [];

    if (!clientesCache.length) {
      tbody.innerHTML = `
        <tr>
          <td colspan="3" class="no-data">No se encontraron clientes.</td>
        </tr>`;
      return;
    }

    renderClientesTable(esTodas);
  } catch (err) {
    console.error("[clientes.js] Error cargando clientes:", err);
    tbody.innerHTML = `
      <tr>
        <td colspan="3" class="no-data" style="color:red;">
          Error al cargar clientes.
        </td>
      </tr>`;
  }
}

// Pinta la tabla usando clientesCache y filtro de búsqueda si hay
function renderClientesTable(esTodas) {
  const tbody = $("#clientes-page-tbody");
  const searchInput = $("#clientes-search");

  if (!tbody) return;

  const q = (searchInput?.value || "").toLowerCase().trim();

  const lista = clientesCache.filter((cliente) => {
    const nombreCompleto = `${cliente.nombre_usuario || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`
      .trim()
      .toLowerCase();

    const email = (cliente.email_usuario || "").toLowerCase();

    if (!q) return true;
    return nombreCompleto.includes(q) || email.includes(q);
  });

  if (!lista.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="3" class="no-data">
          No se encontraron clientes que coincidan con la búsqueda.
        </td>
      </tr>`;
    return;
  }

  let html = "";

  lista.forEach((cliente) => {
    const nombreCompleto = `${cliente.nombre_usuario || ""} ${
      cliente.apellido_paterno || ""
    } ${cliente.apellido_materno || ""}`.trim();

    const email = cliente.email_usuario || "(Sin correo)";
    const initials = getInitials(nombreCompleto || email);

    html += "<tr>";

    // 👇 Primera columna: avatar + nombre + email
    html += `
      <td class="cliente-cell">
        <div class="avatar-sm">${initials}</div>
        <div class="cliente-texts">
          <span class="cliente-nombre">${nombreCompleto || "(Sin nombre)"}</span>
          <span class="cliente-email">${email}</span>
        </div>
      </td>
    `;

    // Segunda columna: solo email grande, si quieres puedes quitarla
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

    html += "</tr>";
  });

  tbody.innerHTML = html;
}


// Inicializar eventos
document.addEventListener("DOMContentLoaded", () => {
  console.log("[clientes.js] DOMContentLoaded");

  // Cargar clientes al entrar
  loadClientesPage();

  // Recargar al cambiar sucursal
  $("#admin-sucursal-selector")?.addEventListener("change", () =>
    loadClientesPage()
  );

  // Buscar mientras escribe
  $("#clientes-search")?.addEventListener("input", () => {
    const sucursalId = $("#admin-sucursal-selector")?.value || "all";
    const esTodas = sucursalId === "all";
    renderClientesTable(esTodas);
  });
});
