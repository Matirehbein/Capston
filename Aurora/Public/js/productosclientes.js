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
  console.log("[productosclientes.js] Iniciando loadProducts...");
  const grid = $("#store-products-grid");
  const pageTitleElement = document.querySelector(".section-title h2");
  if (!grid) return console.error("Error: #store-products-grid no encontrado.");

  grid.innerHTML = Array(8).fill(0).map(skeletonCard).join("");

  // --- Detectar tipo de filtro ---
  let categoria = null;
  const hash = window.location.hash;
  if (hash && hash.startsWith("#categoria=")) {
    categoria = decodeURIComponent(hash.substring("#categoria=".length));
  }

  // --- Leer colección (desde sessionStorage, usada en verano.html, etc.) ---
  const coleccion = sessionStorage.getItem("coleccion_filtro") || null;
  console.log("[productosclientes.js] Colección activa:", coleccion);

  // --- Configurar título dinámico ---
  if (coleccion && pageTitleElement) {
    pageTitleElement.textContent = `Colección ${coleccion}`;
  } else if (categoria && pageTitleElement) {
    pageTitleElement.textContent =
      categoria.charAt(0).toUpperCase() + categoria.slice(1).toLowerCase();
  } else if (pageTitleElement) {
    pageTitleElement.textContent = "Nuestros Productos";
  }

  try {
    // --- Construcción de URL según filtro activo ---
    let apiUrl = `${API_BASE}/api/productos_public`;

    const params = new URLSearchParams();
    if (coleccion) params.append("coleccion", coleccion);
    else if (categoria) params.append("categoria", categoria);

    if (params.toString()) apiUrl += `?${params.toString()}`;
    console.log("[productosclientes.js] URL API final:", apiUrl);

    // --- Petición a la API ---
    const res = await fetch(apiUrl, {
      headers: { Accept: "application/json" },
      credentials: "include",
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

    const data = await res.json();
    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<div class="empty-state"><p>No hay productos disponibles ${
        coleccion
          ? `en la colección "${coleccion}".`
          : categoria
          ? `en la categoría "${categoria}".`
          : "actualmente."
      }</p></div>`;
      return;
    }

    grid.innerHTML = data.map(productCard).join("");

    // --- Listeners (igual que antes) ---
    grid.addEventListener("click", (e) => {
      const wrapper = e.target.closest(".producto-link-wrapper");
      if (wrapper) {
        e.preventDefault();
        const id = wrapper.dataset.id;
        if (id) window.location.href = `detalle_producto.html#id=${id}`;
        return;
      }

      const btn = e.target.closest(".btn-add-cart");
      if (btn) {
        const id = Number(btn.dataset.id);
        const name = decodeURIComponent(btn.dataset.name || "");
        const price = Number(btn.dataset.price || 0);
        const image = btn.dataset.img || "../Public/imagenes/placeholder.jpg";
        const sku = btn.dataset.sku || `prod-${id}`;
        addItem({ id, name, price, image, sku, variation: { talla: "Única" } }, 1);
        const prev = btn.textContent;
        btn.textContent = "¡Añadido!";
        btn.disabled = true;
        setTimeout(() => {
          btn.textContent = prev;
          btn.disabled = false;
        }, 900);
      }
    });

  } catch (err) {
    console.error("[productosclientes.js] Error:", err);
    grid.innerHTML = `<div class="error-state"><p>Ups, no pudimos cargar los productos.</p><pre>${err.message}</pre></div>`;
  } finally {
    // 🔹 Limpia el filtro de colección al terminar, para no afectar otras páginas
    sessionStorage.removeItem("coleccion_filtro");
  }
}


// Se ejecuta cuando el HTML de la página está listo
document.addEventListener("DOMContentLoaded", () => {
  updateCartBadge(); // Actualiza el contador del carrito en el header
  loadProducts();    // Llama a la función principal para cargar productos (leerá el HASH)
});