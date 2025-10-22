// ../Public/js/ofertasclientes.js

// Importa las funciones necesarias, incluyendo updateCartBadge
import { addItem, formatCLP, updateCartBadge } from "./cart.js";

const API_BASE = "http://localhost:5000";
const grid = document.querySelector(".ofertas-grid"); // Mantenido tu selector

/**
 * --- productCard MODIFICADO ---
 * Genera el HTML para un producto dentro de una oferta,
 * usando el mismo formato de precios que productos.html.
 */
function productCard(p, descuento) { // p = producto, descuento = descuento_pct
  const img = p.imagen_url || "/Public/imagenes/placeholder.jpg";
  const nombre = p.nombre_producto || "Producto sin nombre";
  const precioOriginal = Number(p.precio_producto) || 0;
  const descuentoPct = Number(descuento) || 0;

  let displayPriceHtml;
  let precioOferta = precioOriginal;

  if (descuentoPct > 0 && descuentoPct <= 100) {
    precioOferta = Math.round(precioOriginal * (1 - descuentoPct / 100.0));
    displayPriceHtml = `
      <p class="producto-precio-original">${formatCLP(precioOriginal)}</p>
      <p class="producto-precio-oferta">${formatCLP(precioOferta)} <span class="descuento-tag">-${Math.round(descuentoPct)}%</span></p>
    `;
  } else {
    displayPriceHtml = `<p class="producto-precio">${formatCLP(precioOriginal)}</p>`;
  }

  // --- HTML DE LA TARJETA MODIFICADO ---
  return `
    <article class="producto oferta">
      <a href="detalle_producto.html#id=${p.id_producto}" title="Ver detalle de ${nombre}">
           <img src="${img}" alt="${nombre}" loading="lazy"
                onerror="this.src='/Public/imagenes/placeholder.jpg'"/>
       </a>
      <h3>${nombre}</h3>

      <div class="producto-precio-container">
          ${displayPriceHtml}
      </div>

      <p class="producto-categoria">${p.categoria_producto || 'Sin categoría'}</p>

    </article>
  `;
}


/**
 * Genera el HTML para una sección de oferta completa (sin cambios estructurales)
 */
function ofertaSection(oferta) {
  // Asegúrate de que oferta.productos exista y sea un array
  const productosHtml = Array.isArray(oferta.productos)
      ? oferta.productos.map(p => productCard(p, oferta.descuento_pct)).join("")
      : '<p>No hay productos en esta oferta.</p>'; // Mensaje de fallback

  return `
    <div class="oferta-bloque">
      <h3>${oferta.titulo || 'Oferta'}</h3>
      <p>${oferta.descripcion || ""}</p>
      <div class="productos-grid">
        ${productosHtml}
      </div>
    </div>
  `;
}

/**
 * Carga las ofertas desde la API (sin cambios estructurales)
 */
async function loadOfertas() {
  if (!grid) {
      console.error("Contenedor '.ofertas-grid' principal no encontrado.");
      return;
  }
  grid.innerHTML = "<p>Cargando ofertas...</p>"; // Estado inicial de carga

  try {
    const res = await fetch(`${API_BASE}/api/ofertas_public`, {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });
    // Manejo de errores mejorado
    if (!res.ok) {
        let errorMsg = `Error ${res.status}`;
        try { errorMsg += `: ${await res.text()}`; } catch(_) {}
        throw new Error(errorMsg);
    }
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<div class="empty-state"><p>No hay ofertas disponibles actualmente.</p></div>`;
      return;
    }
    // Renderiza las secciones de oferta
    grid.innerHTML = data.map(ofertaSection).join("");

  } catch (err) {
    console.error("Error al cargar ofertas:", err);
    grid.innerHTML = `<div class="error-state"><p>Error cargando ofertas.</p><pre>${err.message}</pre></div>`;
  }
}

// Delegación para clicks en “Añadir al carrito” (sin cambios estructurales)
grid.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn-add-cart");
  if (!btn) return;

  const id = Number(btn.dataset.id);
  const name = decodeURIComponent(btn.dataset.name || "");
  const price = Number(btn.dataset.price || 0); // Precio (ya con descuento)
  const image = btn.dataset.img || "/Public/imagenes/placeholder.jpg";
  const sku = btn.dataset.sku || `prod-${id}`; // SKU base o fallback
  const originalPrice = Number(btn.dataset.original || 0);
  const discountPct = Number(btn.dataset.discount || 0);

  // Crear item para añadir (asumiendo Talla Única desde esta vista)
  const itemToAdd = {
      id, name, price, image, sku,
      variation: { talla: 'Única' }, // Asumimos Talla Única aquí
      // Opcional: guardar meta info si la necesitas en el carrito
      // meta: { originalPrice, discountPct }
  };

  addItem(itemToAdd, 1); // Añade 1 unidad (addItem maneja el modal)

  // Feedback visual (sin cambios)
  const prevText = btn.textContent;
  btn.textContent = "¡Añadido!";
  btn.disabled = true;
  setTimeout(() => {
    btn.textContent = "Añadir al carrito";
    btn.disabled = false;
  }, 900);
});

/**
 * --- MODIFICADO ---
 * Llama a updateCartBadge y loadOfertas al cargar.
 */
document.addEventListener("DOMContentLoaded", () => {
    updateCartBadge(); // Asegura que el badge esté actualizado al cargar la página
    loadOfertas();
});