// ../Public/js/productosclientes.js

const API_BASE = "http://127.0.0.1:5000"; // ajusta si usas otra IP/puerto
const $ = (s) => document.querySelector(s);

function formatCLP(value) {
  try {
    return Number(value).toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0,
    });
  } catch {
    return `$${value}`;
  }
}

function productCard(p) {
  const img = p.imagen_url || "/Public/imagenes/placeholder.jpg";
  const nombre = p.nombre_producto || "Producto sin nombre";
  const precio = formatCLP(p.precio_producto || 0);

  // Si tienes rutas de detalle, cámbialo a un <a> con href
  return `
    <article class="producto">
      <img src="${img}" alt="${nombre}" loading="lazy" onerror="this.src='/Public/imagenes/placeholder.jpg'"/>
      <h3 title="${nombre}">${nombre}</h3>
      <p class="producto-precio">${precio}</p>
      <button class="btn btn-add-cart" data-id="${p.id_producto}">Añadir al carrito</button>
    </article>
  `;
}

function skeletonCard() {
  return `
    <article class="producto skeleton">
      <div class="sk-img"></div>
      <div class="sk-line"></div>
      <div class="sk-line sm"></div>
      <div class="sk-btn"></div>
    </article>
  `;
}

async function loadProducts() {
  const grid = $("#store-products-grid");
  if (!grid) return;

  // skeletons mientras carga
  grid.innerHTML = new Array(8).fill(0).map(skeletonCard).join("");

  try {
    const res = await fetch(`${API_BASE}/api/productos`, {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!res.ok) {
      throw new Error(await res.text());
    }
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `
        <div class="empty-state">
          <p>No encontramos productos disponibles por ahora.</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = data.map(productCard).join("");

    // (Opcional) manejar clicks en “Añadir al carrito”
    grid.addEventListener("click", (e) => {
      const btn = e.target.closest(".btn-add-cart");
      if (!btn) return;
      const id = btn.dataset.id;
      // TODO: integrar con tu carrito (localStorage / API)
      alert(`Producto ${id} añadido al carrito (demo).`);
    });
  } catch (err) {
    console.error(err);
    grid.innerHTML = `
      <div class="error-state">
        <p>Ups, no pudimos cargar los productos.</p>
        <pre style="white-space:pre-wrap;">${String(err.message || err)}</pre>
      </div>
    `;
  }
}

document.addEventListener("DOMContentLoaded", loadProducts);
