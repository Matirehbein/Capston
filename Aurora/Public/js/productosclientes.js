// ../Public/js/productosclientes.js

// Importamos addItem, formatCLP, y updateCartBadge desde cart.js
import { addItem, formatCLP, updateCartBadge } from "./cart.js";

// URL base del backend Flask
const API_BASE = "http://localhost:5000";
// Selector de conveniencia
const $ = (s) => document.querySelector(s);

/**
 * Genera el HTML para la tarjeta de un producto.
 * Muestra precio original tachado y precio de oferta si aplica.
 */
function productCard(p) {
  const img = p.imagen_url || "../Public/imagenes/placeholder.jpg";
  const nombre = p.nombre_producto || "Producto sin nombre";
  const precioOriginal = p.precio_producto || 0;
  const precioOferta = p.precio_oferta;
  const descuentoPct = p.descuento_pct;

  let displayPriceHtml;
  // (La lógica de precios sigue igual)
  if (precioOferta !== null && precioOferta !== undefined && precioOferta < precioOriginal) {
    displayPriceHtml = `<p class="producto-precio-original">${formatCLP(precioOriginal)}</p><p class="producto-precio-oferta">${formatCLP(precioOferta)} ${descuentoPct ? `<span class="descuento-tag">-${Math.round(descuentoPct)}%</span>` : ''}</p>`;
  } else {
    displayPriceHtml = `<p class="producto-precio">${formatCLP(precioOriginal)}</p>`;
  }

  // --- HTML DE LA TARJETA MODIFICADO ---
  return `
    <article class="producto">
      <div class="producto-link-wrapper"
           title="Ver detalle de ${nombre}"
           data-id="${p.id_producto}"
           role="button"
           tabindex="0">
        <img src="${img}" alt="${nombre}" loading="lazy"
             onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
        <h3 title="${nombre}">${nombre}</h3>
      </div>

      <div class="producto-precio-container">
          ${displayPriceHtml}
      </div>

      <p class="producto-categoria">${p.categoria_producto || 'Sin categoría'}</p>

    </article>
  `;
}

/**
 * Genera el HTML para una tarjeta "esqueleto" mientras cargan los datos.
 */
function skeletonCard() {
  return `
    <article class="producto skeleton">
      <div class="sk-img"></div> <div class="sk-line"></div>
      <div class="sk-line sm"></div> <div class="sk-btn"></div>
    </article>
  `;
}

/**
 * --- loadProducts MODIFICADO ---
 * Lee la categoría desde el HASH (#categoria=...) de la URL.
 */
async function loadProducts() {
  console.log("[productosclientes.js] Iniciando loadProducts..."); // DEBUG
  const grid = $("#store-products-grid");
  const pageTitleElement = document.querySelector('.section-title h2'); // Título H2

  if (!grid) { console.error('Error: Contenedor #store-products-grid no encontrado.'); return; }

  grid.innerHTML = Array(8).fill(0).map(skeletonCard).join(""); // Muestra esqueletos

  // --- ▼▼▼ LEER CATEGORÍA DESDE EL HASH (#) ▼▼▼ ---
  console.log("[productosclientes.js] URL Completa:", window.location.href); // DEBUG
  console.log("[productosclientes.js] URL Hash:", window.location.hash); // DEBUG

  let categoria = null;
  const hash = window.location.hash; // Ej: #categoria=Abrigos

  // Verifica si el hash existe y empieza con #categoria=
  if (hash && hash.startsWith('#categoria=')) {
      // Extrae el valor después de #categoria= y decodifica caracteres especiales (como espacios %20)
      categoria = decodeURIComponent(hash.substring('#categoria='.length));
  }
  console.log("[productosclientes.js] Categoría leída desde Hash:", categoria); // DEBUG
  // --- ▲▲▲ FIN LEER HASH ▲▲▲ ---

  // Actualiza el título H2 si se está filtrando por categoría
  if (categoria && pageTitleElement) {
    pageTitleElement.textContent = categoria.charAt(0).toUpperCase() + categoria.slice(1).toLowerCase();
  } else if (pageTitleElement) {
    pageTitleElement.textContent = "Nuestros Productos"; // Título por defecto
  }

  try {
    // --- CONSTRUIR URL DE LA API ---
    // La API sigue esperando el parámetro con '?', no con '#'
    let apiUrl = `${API_BASE}/api/productos_public`;
    if (categoria) { // Solo si se encontró una categoría en el hash...
      apiUrl += `?categoria=${encodeURIComponent(categoria)}`; // ...añádela como parámetro de consulta '?'
    }
    console.log("[productosclientes.js] URL API final:", apiUrl); // DEBUG
    // --- FIN CONSTRUIR URL ---

    // Llama a la API (con o sin filtro de categoría)
    const res = await fetch(apiUrl, {
      headers: { Accept: "application/json" }, credentials: "include"
    });

    // Manejo de errores de la respuesta
    if (!res.ok) {
        let errorMsg = `HTTP ${res.status}`;
        try { errorMsg += `: ${await res.text()}`; } catch(_) {} // Intenta obtener cuerpo del error
        throw new Error(errorMsg);
    }

    const data = await res.json(); // Convierte la respuesta a JSON

    // Comprueba si la respuesta es válida y tiene productos
    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<div class="empty-state"><p>No hay productos disponibles${categoria ? ` en la categoría "${categoria}"` : ''}.</p></div>`;
      return; // No hacer nada más si no hay productos
    }

    // Si hay productos, genera el HTML y lo inserta en la grilla
    grid.innerHTML = data.map(productCard).join("");

    // --- Listener de Clics (Delegación - SIN CAMBIOS) ---
    grid.addEventListener("click", (e) => {
      // 1. Clic para ver detalle (en el wrapper de imagen/título)
      const wrapper = e.target.closest(".producto-link-wrapper");
      if (wrapper) {
        e.preventDefault(); // Evita comportamiento por defecto si fuera un <a>
        const id = wrapper.dataset.id;
        if (id) {
            // Asegúrate que la navegación a detalle también use HASH si es necesario
            window.location.href = `detalle_producto.html#id=${id}`;
        }
        return; // Detiene la ejecución aquí
      }

      // 2. Clic en el botón "Añadir al carrito"
      const btn = e.target.closest(".btn-add-cart");
      if (btn) {
        const id = Number(btn.dataset.id);
        const name = decodeURIComponent(btn.dataset.name || "");
        const price = Number(btn.dataset.price || 0); // Precio (ya es el final con/sin oferta)
        const image = btn.dataset.img || "../Public/imagenes/placeholder.jpg";
        const sku = btn.dataset.sku || `prod-${id}`; // SKU base o fallback si no hay específico

        // Crea el objeto a añadir (asume Talla Única desde la grilla general)
        const itemToAdd = { id, name, price, image, sku, variation: { talla: 'Única' } };
        addItem(itemToAdd, 1); // Llama a la función de cart.js para añadir (y mostrar modal)

        // Feedback visual en el botón
        const prev = btn.textContent; btn.textContent = "¡Añadido!"; btn.disabled = true;
        setTimeout(() => { btn.textContent = prev; btn.disabled = false; }, 900);
        return; // Detiene la ejecución aquí
      }
    });
    // --- Fin Listener ---

  } catch (err) {
    // Muestra un error si falla la carga de productos
    console.error(`[productos${categoria ? `/${categoria}` : ''}] Error cargando productos:`, err);
    grid.innerHTML = `<div class="error-state"><p>Ups, no pudimos cargar los productos.</p><pre>${err.message}</pre></div>`;
  }
}

// Se ejecuta cuando el HTML de la página está listo
document.addEventListener("DOMContentLoaded", () => {
  updateCartBadge(); // Actualiza el contador del carrito en el header
  loadProducts();    // Llama a la función principal para cargar productos (leerá el HASH)
});