// ../Public/js/ofertasclientes.js
import { addItem, formatCLP } from "./cart.js";

const API_BASE = "http://127.0.0.1:5000";
const grid = document.querySelector(".ofertas-grid");

function productCard(p, descuento) {
  const img = p.imagen_url || "/Public/imagenes/placeholder.jpg";
  const original = Number(p.precio_producto);
  const rebajado = Math.max(0, original * (1 - Number(descuento) / 100));

  return `
    <article class="producto oferta">
      <img src="${img}" alt="${p.nombre_producto}" loading="lazy" onerror="this.src='/Public/imagenes/placeholder.jpg'"/>
      <h3>${p.nombre_producto}</h3>
      <p class="precio-original">${formatCLP(original)}</p>
      <p class="precio-rebajado">${formatCLP(rebajado)}</p>
      <span class="badge-descuento">-${descuento}%</span>

      <button class="btn btn-add-cart"
        data-id="${p.id_producto}"
        data-name="${encodeURIComponent(p.nombre_producto)}"
        data-img="${img}"
        data-sku="${p.sku || ""}"
        data-price="${rebajado}"
        data-original="${original}"
        data-discount="${descuento}">
        Añadir al carrito
      </button>
    </article>
  `;
}

function ofertaSection(oferta) {
  return `
    <div class="oferta-bloque">
      <h3>${oferta.titulo}</h3>
      <p>${oferta.descripcion || ""}</p>
      <div class="productos-grid">
        ${oferta.productos.map(p => productCard(p, oferta.descuento_pct)).join("")}
      </div>
    </div>
  `;
}

async function loadOfertas() {
  grid.innerHTML = "<p>Cargando ofertas...</p>";
  try {
    const res = await fetch(`${API_BASE}/api/ofertas_public`, {
      credentials: "include",
      headers: { "Accept": "application/json" }
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<p>No hay ofertas disponibles actualmente.</p>`;
      return;
    }
    grid.innerHTML = data.map(ofertaSection).join("");
  } catch (err) {
    console.error(err);
    grid.innerHTML = `<p>Error cargando ofertas.</p>`;
  }
}

// Delegación para clicks en “Añadir al carrito”
grid.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn-add-cart");
  if (!btn) return;

  const id = Number(btn.dataset.id);
  const name = decodeURIComponent(btn.dataset.name || "");
  const price = Number(btn.dataset.price || 0);            // precio con descuento
  const image = btn.dataset.img || "/Public/imagenes/placeholder.jpg";
  const sku = btn.dataset.sku || null;

  // Puedes guardar info adicional (original/discount) en el item.meta si tu cart lo soporta
  addItem({ id, name, price, image, sku, meta: {
    originalPrice: Number(btn.dataset.original || 0),
    discountPct: Number(btn.dataset.discount || 0)
  }}, 1);

  btn.textContent = "¡Añadido!";
  btn.disabled = true;
  setTimeout(() => {
    btn.textContent = "Añadir al carrito";
    btn.disabled = false;
  }, 900);
});

document.addEventListener("DOMContentLoaded", loadOfertas);
