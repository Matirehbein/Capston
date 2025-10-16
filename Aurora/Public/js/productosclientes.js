// ../Public/js/productosclientes.js
import { addItem, formatCLP } from "./cart.js";

const API_BASE = "http://127.0.0.1:5000";
const $ = (s) => document.querySelector(s);

function productCard(p) {
  const img = p.imagen_url || "../Public/imagenes/placeholder.jpg";
  const nombre = p.nombre_producto || "Producto sin nombre";
  const precio = formatCLP(p.precio_producto || 0);
  
  // ¡ESTA LÍNEA ES LA QUE GENERA EL ENLACE CORRECTO!
  const detailUrl = `detalle_producto.html?id=${p.id_producto}`; 

  return `
    <a href="${detailUrl}" class="producto-link">
      <article class="producto">
        <img src="${img}" alt="${nombre}" loading="lazy"
             onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
        <h3 title="${nombre}">${nombre}</h3>
        <p class="producto-precio">${precio}</p>
        <button class="btn">Ver Detalles</button>
      </article>
    </a>
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
  if (!grid) {
    console.error('No existe el contenedor con id="store-products-grid"');
    return;
  }

  grid.innerHTML = new Array(8).fill(0).map(skeletonCard).join("");

  try {
    const res = await fetch(`${API_BASE}/api/productos_public`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `<div class="empty-state"><p>No encontramos productos disponibles por ahora.</p></div>`;
      return;
    }

    grid.innerHTML = data.map(productCard).join("");

  } catch (err) {
    console.error("[productos] error:", err);
    grid.innerHTML = `<div class="error-state"><p>Ups, no pudimos cargar los productos.</p></div>`;
  }
}

document.addEventListener("DOMContentLoaded", loadProducts);