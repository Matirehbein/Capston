// ../Public/Js/geolocation.js

const API_BASE = "http://localhost:5000"; // URL de tu backend Flask
const BRANCH_ID_KEY = 'nearestBranchId'; // Key for sessionStorage
const BRANCH_NAME_KEY = 'nearestBranchName'; // Key for sessionStorage

/**
 * --- NUEVO: Exporta funciones para obtener los datos guardados ---
 */
export function getNearestBranchId() {
  return sessionStorage.getItem(BRANCH_ID_KEY);
}
export function getNearestBranchName() {
  return sessionStorage.getItem(BRANCH_NAME_KEY);
}
/**
 * --- FIN NUEVAS EXPORTACIONES ---
 */


/**
 * --- FUNCIÓN PRINCIPAL (AHORA EXPORTADA) ---
 * Pide geolocalización, busca la sucursal más cercana y la guarda en sessionStorage.
 * Actualiza el elemento HTML con id 'nearest-branch-display'.
 */
export function findAndStoreNearestBranch() {
  const displayElement = document.getElementById('nearest-branch-display');
  // Es normal que en algunas páginas no exista este elemento, no mostrar error.
  // if (!displayElement) {
  //   console.log("Elemento 'nearest-branch-display' no encontrado en esta página.");
  // }

  if (!navigator.geolocation) {
    if (displayElement) displayElement.textContent = "Geoloc. no soportada";
    clearStoredBranch(); // Limpiar por si acaso
    return;
  }

  if (displayElement) displayElement.textContent = "Obteniendo ubicación...";

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const userLat = position.coords.latitude;
      const userLon = position.coords.longitude;
      // console.log(`Ubicación: Lat ${userLat}, Lon ${userLon}`);
      if (displayElement) displayElement.textContent = "Buscando sucursales...";

      try {
        const response = await fetch(`${API_BASE}/api/sucursales_con_coords`);
        if (!response.ok) throw new Error(`Error ${response.status}`);
        const branches = await response.json();
        // console.log("Sucursales:", branches);

        if (!branches || branches.length === 0) {
          if (displayElement) displayElement.textContent = "No hay sucursales";
          clearStoredBranch();
          return;
        }

        let nearestBranch = null;
        let minDistance = Infinity;

        branches.forEach(branch => {
          if (typeof branch.latitud === 'number' && typeof branch.longitud === 'number') {
            const distance = calculateDistance(userLat, userLon, branch.latitud, branch.longitud);
            if (distance < minDistance) {
              minDistance = distance;
              nearestBranch = branch;
            }
          }
        });

        if (nearestBranch) {
          // console.log("Sucursal más cercana:", nearestBranch);
          if (displayElement) displayElement.textContent = `📍 ${nearestBranch.nombre_sucursal}`;
          // Guardar en sessionStorage
          sessionStorage.setItem(BRANCH_ID_KEY, nearestBranch.id_sucursal);
          sessionStorage.setItem(BRANCH_NAME_KEY, nearestBranch.nombre_sucursal);
          // console.log(`Sucursal ${nearestBranch.id_sucursal} guardada.`);

          // Disparar un evento personalizado para notificar a otros scripts
          window.dispatchEvent(new CustomEvent('branchLocated', { detail: nearestBranch }));

        } else {
          if (displayElement) displayElement.textContent = "No se encontró sucursal";
          clearStoredBranch();
        }

      } catch (error) {
        console.error("Error buscando sucursal:", error);
        if (displayElement) displayElement.textContent = "Error buscando";
        clearStoredBranch();
      }
    },
    (error) => {
      console.error("Error Geoloc:", error);
      let message = "No se pudo obtener ubicación";
      if (error.code === error.PERMISSION_DENIED) message = "Permiso denegado";
      // ... (otros códigos de error si quieres)
      if (displayElement) displayElement.textContent = message;
      clearStoredBranch(); // Limpiar si falla
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
  );
}

// Limpia los datos guardados
function clearStoredBranch() {
    sessionStorage.removeItem(BRANCH_ID_KEY);
    sessionStorage.removeItem(BRANCH_NAME_KEY);
    // Dispara evento para notificar que no se encontró/pudo obtener
    window.dispatchEvent(new Event('branchLocationCleared'));
}


// --- Funciones de cálculo de distancia (sin cambios) ---
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

// --- Ejecución inicial ---
// Intenta encontrar la sucursal apenas se carga este script
// Esto se ejecutará en CADA página que incluya geolocation.js
findAndStoreNearestBranch();