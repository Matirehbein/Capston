const API_BASE = "http://localhost:5000";
let map;   

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  loadSucursales();
});

// -------------------------------------
// Inicializar Mapa
// -------------------------------------
function initMap() {
  map = L.map("map", {
    minZoom: 2  // ✅ evita zooms negativos raros
  }).setView([-33.45, -70.66], 6);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    noWrap: true,
    worldCopyJump: false
  }).addTo(map);

  setTimeout(() => {
    map.invalidateSize();
  }, 300);
}



// -------------------------------------
// Icono de sucursal (opcional)
// -------------------------------------
const sucursalIcon = L.icon({
  iconUrl: "/Public/img/marker-sucursal.png",
  iconSize: [38, 38],
  iconAnchor: [19, 38],
  popupAnchor: [0, -34],
});

// -------------------------------------
// Cargar sucursales
// -------------------------------------
async function loadSucursales() {
  try {
    const res = await fetch(`${API_BASE}/api/sucursales_publicas`);
    const sucursales = await res.json();

    renderSucursales(sucursales);
    renderMarkers(sucursales);

  } catch (err) {
    console.error("❌ Error cargando sucursales:", err);
  }
}

// -------------------------------------
// Render tarjetas PREMIUM
// -------------------------------------
function renderSucursales(sucursales) {
  const grid = document.getElementById("branchesGrid");
  grid.innerHTML = "";

  sucursales.forEach((s) => {
    const div = document.createElement("div");
    div.className = "branch-card";

    const horarioHTML = formatHorario(s.horario_json); // <-- JSONB

    div.innerHTML = `
      <div class="branch-header">
        <h3>${s.nombre_sucursal}</h3>
        <span class="branch-badge">${s.region_sucursal}</span>
      </div>

      <p class="branch-address">
        📍 ${s.direccion_sucursal}, ${s.comuna_sucursal}
      </p>

      <p class="branch-phone">
        📞 ${s.telefono_sucursal || "No disponible"}
      </p>

      <div class="branch-horario-box">
        <strong>Horario:</strong>
        ${horarioHTML}
      </div>

      <div class="branch-actions">
        <button 
          class="btn-map"
          data-lat="${s.latitud_sucursal}"
          data-lng="${s.longitud_sucursal}"
        >
          Ver en el mapa
        </button>
      </div>
    `;

    div.querySelector(".btn-map").addEventListener("click", () => {
      if (!s.latitud_sucursal || !s.longitud_sucursal) return;

      map.setView(
        [s.latitud_sucursal, s.longitud_sucursal],
        16,
        { animate: true }
      );
    });

    grid.appendChild(div);
  });
}

// -------------------------------------
// Render Marcadores
// -------------------------------------
function renderMarkers(sucursales) {
  const bounds = [];

  sucursales.forEach((s) => {
    if (!s.latitud_sucursal || !s.longitud_sucursal) return;

    const marker = L.marker(
      [s.latitud_sucursal, s.longitud_sucursal],
    ).addTo(map);

    marker.bindPopup(`
      <strong>${s.nombre_sucursal}</strong><br>
      ${s.direccion_sucursal}, ${s.comuna_sucursal}<br>
      Región: ${s.region_sucursal}<br>
      Tel: ${s.telefono_sucursal || "No disponible"}<br><br>

      <a 
        target="_blank"
        href="https://www.google.com/maps?q=${s.latitud_sucursal},${s.longitud_sucursal}"
        style="color:#5e745e; font-weight:600; text-decoration:none;"
      >
        Cómo llegar →
      </a>
    `);

    bounds.push([
      s.latitud_sucursal,
      s.longitud_sucursal
    ]);
  });

  if (bounds.length > 0) {
    map.fitBounds(bounds, { padding: [40, 40] });
  }
}

function formatHorario(horario_json) {
  if (!horario_json || typeof horario_json !== "object") {
    return "<span class='horario-cerrado'>Horario no disponible</span>";
  }

  let html = "<div class='branch-horario'>";

  for (const dia in horario_json) {
    let valor = horario_json[dia];

    // Si está cerrado
    if (typeof valor === "string" && valor.toLowerCase().includes("cerrado")) {
      html += `
        <div class="horario-row">
          <span class="dia">${capitalizar(dia)}</span>
          <span class="hora horario-cerrado">Cerrado</span>
        </div>
      `;
      continue;
    }

    // Normalizar formato hora
    const [inicio, fin] = valor.split("-").map(h => normalizarHora(h));

    html += `
      <div class="horario-row">
        <span class="dia">${capitalizar(dia)}</span>
        <span class="hora">${inicio} - ${fin}</span>
      </div>
    `;
  }

  html += "</div>";
  return html;
}

/* ============================= */
/* FUNCIONES DE APOYO            */
/* ============================= */

function normalizarHora(hora) {
  if (!hora) return "00:00";

  // Si viene solo como "9" → "09:00"
  if (!hora.includes(":")) {
    return hora.padStart(2, "0") + ":00";
  }

  let [h, m] = hora.split(":");
  h = h.padStart(2, "0");
  m = m.padStart(2, "0");

  return `${h}:${m}`;
}

function capitalizar(texto) {
  return texto.charAt(0).toUpperCase() + texto.slice(1).toLowerCase();
}
