// ../Public/Js/geolocation.js

const API_BASE = "http://localhost:5000";
const GEO_BRANCH_ID_KEY = 'nearestBranchId';     // (Session) Para la sucursal geolocalizada
const GEO_BRANCH_NAME_KEY = 'nearestBranchName';
const MANUAL_BRANCH_ID_KEY = 'manualBranchId';   // (Local) Para la sucursal elegida manualmente
const MANUAL_BRANCH_NAME_KEY = 'manualBranchName';

/**
 * --- FUNCIONES EXPORTADAS (Para otros scripts como detalle_producto.js) ---
 */

/**
 * Obtiene el ID de la sucursal ACTIVA.
 * Prioriza la elección manual del usuario sobre la geolocalización.
 */
export function getActiveBranchId() {
  const manualId = localStorage.getItem(MANUAL_BRANCH_ID_KEY);
  if (manualId) {
    // console.log("Usando ID manual:", manualId);
    return manualId;
  }
  const geoId = sessionStorage.getItem(GEO_BRANCH_ID_KEY);
  // console.log("Usando ID geolocalizado:", geoId);
  return geoId; // Será null si no hay ni manual ni geo
}

/**
 * Obtiene el NOMBRE de la sucursal ACTIVA.
 */
export function getActiveBranchName() {
  const manualName = localStorage.getItem(MANUAL_BRANCH_NAME_KEY);
  if (manualName) {
    return manualName;
  }
  return sessionStorage.getItem(GEO_BRANCH_NAME_KEY);
}

// --- LÓGICA PRINCIPAL DEL SCRIPT ---

// Se ejecuta en CADA carga de página
document.addEventListener('DOMContentLoaded', () => {
  setupBranchSelectorListeners(); // 1. Prepara los clics del menú
  fetchAllBranchesAndPopulateDropdown(); // 2. Rellena el menú con todas las sucursales
  determineInitialBranch(); // 3. Decide qué mostrar: manual o geolocalizar
});

/**
 * LÓGICA CLAVE: Decide qué sucursal mostrar al cargar la página.
 */
function determineInitialBranch() {
  const manualBranchName = localStorage.getItem(MANUAL_BRANCH_NAME_KEY);
  
  if (manualBranchName) {
    // 1. SI HAY MANUAL: El usuario ya eligió. Solo mostramos esa.
    console.log(`[Geo] Cargando sucursal manual guardada: ${manualBranchName}`);
    updateBranchDisplay(manualBranchName);
  } else {
    // 2. SI NO HAY MANUAL: Ejecutamos la geolocalización automática (como antes).
    console.log("[Geo] No hay sucursal manual, iniciando geolocalización...");
    findAndStoreNearestBranch(); 
  }
}

/**
 * (Esta es tu función original "buena")
 * Pide permiso de geolocalización, encuentra la más cercana y la guarda.
 * Es llamada por determineInitialBranch (si no hay manual) O al hacer clic en "Usar mi ubicación".
 */
function findAndStoreNearestBranch() {
  const displayElement = document.getElementById('branch-display-btn');
  if (!displayElement) return; // No hay dónde mostrar

  if (!navigator.geolocation) {
    displayElement.textContent = "Geoloc. no soportada";
    clearStoredBranch('geo'); // Limpia solo la parte de geo
    return;
  }

  displayElement.textContent = "📍 Obteniendo ubicación...";

  // Solicita la posición
  navigator.geolocation.getCurrentPosition(
    async (position) => { // ÉXITO
      const userLat = position.coords.latitude;
      const userLon = position.coords.longitude;
      if (displayElement) displayElement.textContent = "📍 Buscando...";

      try {
        // Llama a la API de sucursales (que ya tienes)
        const response = await fetch(`${API_BASE}/api/sucursales_con_coords`);
        if (!response.ok) throw new Error(`Error ${response.status}`);
        const branches = await response.json();

        if (!branches || branches.length === 0) {
          if (displayElement) displayElement.textContent = "No hay sucursales";
          clearStoredBranch('geo'); return;
        }

        // Encuentra la más cercana
        const nearestBranch = findNearest(branches, userLat, userLon);

        if (nearestBranch) {
          // Guarda en sessionStorage (se borra al cerrar el navegador)
          sessionStorage.setItem(GEO_BRANCH_ID_KEY, nearestBranch.id_sucursal);
          sessionStorage.setItem(GEO_BRANCH_NAME_KEY, nearestBranch.nombre_sucursal);
          
          updateBranchDisplay(nearestBranch.nombre_sucursal); // Actualiza el botón
          dispatchBranchUpdate(nearestBranch); // Notifica a detalle_producto.js
        } else {
          if (displayElement) displayElement.textContent = "No se encontró sucursal";
          clearStoredBranch('geo');
        }
      } catch (error) { console.error("Error buscando sucursal (geo):", error); if (displayElement) displayElement.textContent = "Error buscando"; clearStoredBranch('geo'); }
    },
    (error) => { // ERROR (permiso denegado, etc.)
      console.error("Error Geoloc:", error);
      let message = "No se pudo obtener ubicación";
      if (error.code === error.PERMISSION_DENIED) message = "Permiso denegado";
      if (displayElement) displayElement.textContent = message;
      clearStoredBranch('geo'); // Limpia si falla
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 } // Opciones de geolocalización
  );
}

/**
 * Busca TODAS las sucursales y las añade al menú desplegable.
 */
async function fetchAllBranchesAndPopulateDropdown() {
  const dropdownMenu = document.getElementById('branch-list-dropdown');
  if (!dropdownMenu) return; // No hay menú en esta página

  try {
    const response = await fetch(`${API_BASE}/api/sucursales_con_coords`);
    if (!response.ok) throw new Error(`Error ${response.status}`);
    const allBranches = await response.json();

    if (!allBranches || allBranches.length === 0) {
      dropdownMenu.innerHTML = '<div class="dropdown-loading">No hay sucursales.</div>';
      return;
    }

    const currentActiveId = getActiveBranchId(); // ID de la sucursal activa (manual o geo)

    // Construir HTML del menú
    let html = '';
    html += `<a href="#" class="branch-geo-option" data-action="geolocate">Usar mi ubicación (más cercana)</a>`;
    html += `<div class="branch-dropdown-divider"></div>`;
    html += `<div class="branch-dropdown-header">Elegir sucursal</div>`;

    allBranches.forEach(branch => {
      // Compara IDs como strings para evitar errores de tipo
      const isActive = String(branch.id_sucursal) === String(currentActiveId);
      html += `
        <a href="#" 
           class="branch-option ${isActive ? 'active' : ''}" 
           data-id="${branch.id_sucursal}" 
           data-name="${branch.nombre_sucursal}">
          ${branch.nombre_sucursal}
        </a>`;
    });
    dropdownMenu.innerHTML = html;

  } catch (error) {
    console.error("Error al rellenar menú de sucursales:", error);
    dropdownMenu.innerHTML = '<div class="dropdown-loading">Error al cargar.</div>';
  }
}

/**
 * Configura los listeners para el botón y las opciones del menú.
 */
function setupBranchSelectorListeners() {
  const displayBtn = document.getElementById('branch-display-btn');
  const dropdownMenu = document.getElementById('branch-list-dropdown');
  if (!displayBtn || !dropdownMenu) return; // No hay menú, no hacer nada

  // 1. Abrir/Cerrar menú
  displayBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Evita que el listener 'document' lo cierre
    const isVisible = dropdownMenu.style.display === 'block';
    dropdownMenu.style.display = isVisible ? 'none' : 'block';
    // Opcional: Recargar la lista cada vez que se abre para marcar la activa
    if (!isVisible) fetchAllBranchesAndPopulateDropdown();
  });

  // 2. Cerrar menú al hacer clic fuera
  document.addEventListener('click', (e) => {
    // Si el clic NO fue en el botón Y NO fue dentro del menú, ciérralo
    if (displayBtn && !displayBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
      dropdownMenu.style.display = 'none';
    }
  });

  // 3. Manejar clics DENTRO del menú (delegación)
  dropdownMenu.addEventListener('click', (e) => {
    e.preventDefault(); // Evita que el `href="#`" mueva la página
    
    const target = e.target.closest('a'); // Asegura que se hizo clic en un enlace <a>
    if (!target) return; // Si no es un <a>, no hacer nada

    // Opción A: "Usar mi ubicación"
    if (target.classList.contains('branch-geo-option')) {
      console.log("Acción: Geolocalizar");
      clearStoredBranch('manual'); // BORRA la elección manual guardada
      findAndStoreNearestBranch(); // Fuerza la geolocalización (tu función original)
      dropdownMenu.style.display = 'none'; // Cierra menú
      return;
    }

    // Opción B: Clic en una sucursal específica
    if (target.classList.contains('branch-option')) {
      const id = target.dataset.id;
      const name = target.dataset.name;
      console.log(`Acción: Selección manual - ${name} (ID: ${id})`);
      
      // Guarda como elección MANUAL (localStorage, persiste)
      localStorage.setItem(MANUAL_BRANCH_ID_KEY, id);
      localStorage.setItem(MANUAL_BRANCH_NAME_KEY, name);
      // Limpia la elección GEO (la manual tiene prioridad)
      clearStoredBranch('geo');

      updateBranchDisplay(name); // Actualiza el botón
      dropdownMenu.style.display = 'none'; // Cierra menú
      
      // Actualiza la clase 'active' en el menú
      dropdownMenu.querySelectorAll('a.branch-option').forEach(a => a.classList.remove('active'));
      target.classList.add('active');

      // Notifica a otras partes de la página que la sucursal cambió
      dispatchBranchUpdate({ id_sucursal: id, nombre_sucursal: name });
    }
  });
}

// --- FUNCIONES DE AYUDA (Helpers) ---

/**
 * Actualiza el texto del botón principal (con el prefijo).
 */
function updateBranchDisplay(name) {
  const displayBtn = document.getElementById('branch-display-btn');
  if (displayBtn) {
    // Añade el prefijo "Sucursal -"
    displayBtn.textContent = `📍 Sucursal - ${name}`;
  }
}

/**
 * Limpia el almacenamiento (session para geo, local para manual)
 */
function clearStoredBranch(type = 'all') { // 'geo', 'manual', 'all'
  if (type === 'geo' || type === 'all') {
    sessionStorage.removeItem(GEO_BRANCH_ID_KEY);
    sessionStorage.removeItem(GEO_BRANCH_NAME_KEY);
  }
  if (type === 'manual' || type === 'all') {
    localStorage.removeItem(MANUAL_BRANCH_ID_KEY);
    localStorage.removeItem(MANUAL_BRANCH_NAME_KEY);
  }
}

/**
 * Notifica a otros scripts (como detalle_producto.js) que la sucursal cambió.
 */
function dispatchBranchUpdate(branchData) {
  // Dispara un evento personalizado
  window.dispatchEvent(new CustomEvent('branchLocated', { detail: branchData }));
}

/**
 * Encuentra la sucursal más cercana de una lista.
 */
function findNearest(branches, userLat, userLon) {
    let nearestBranch = null;
    let minDistance = Infinity;
    branches.forEach(branch => {
        // Asegura que las coordenadas sean números válidos
        const branchLat = parseFloat(branch.latitud);
        const branchLon = parseFloat(branch.longitud);
        if (!isNaN(branchLat) && !isNaN(branchLon)) {
            const distance = calculateDistance(userLat, userLon, branchLat, branchLon);
            if (distance < minDistance) {
                minDistance = distance;
                nearestBranch = branch;
            }
        }
    });
    return nearestBranch;
}

/**
 * Calcula la distancia entre dos puntos geográficos (Fórmula de Haversine).
 */
function calculateDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Radio de la Tierra en km
  const dLat = deg2rad(lat2 - lat1);
  const dLon = deg2rad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  const d = R * c; // Distancia en km
  return d;
}

function deg2rad(deg) {
  return deg * (Math.PI / 180);
}