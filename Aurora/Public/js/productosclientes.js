// ../Public/js/productosclientes.js



import { addItem, formatCLP } from "./cart.js";



const API_BASE = "http://localhost:5000"; // ajusta si usas otra IP/puerto

const $ = (s) => document.querySelector(s);



/**

 * CAMBIO ESTRUCTURAL:

 * La tarjeta ya no usa un <a>.

 * Ahora usa un <div> con un atributo 'data-id'

 * y 'role="button"' para simular un enlace.

 */

function productCard(p) {

  const img = p.imagen_url || "../Public/imagenes/placeholder.jpg";

  const nombre = p.nombre_producto || "Producto sin nombre";

  const precio = formatCLP(p.precio_producto || 0);



  // Ya no generamos 'detailUrl' aquí.

 

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

     

      <p class="producto-precio">${precio}</p>

      <button class="btn btn-add-cart"

              data-id="${p.id_producto}"

              data-name="${encodeURIComponent(nombre)}"

              data-price="${p.precio_producto || 0}"

              data-sku="${p.sku || ""}"

              data-img="${img}">

        Añadir al carrito

      </button>

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



// Reemplaza ESTA FUNCIÓN COMPLETA en productosclientes.js

async function loadProducts() {
  const grid = $("#store-products-grid");
  if (!grid) {
    console.error('No existe el contenedor con id="store-products-grid"');
    return;
  }

  grid.innerHTML = new Array(8).fill(0).map(skeletonCard).join("");

  try {
    const res = await fetch(`${API_BASE}/api/productos_public`, {
      headers: { Accept: "application/json" },
      credentials: "include"
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);

    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      grid.innerHTML = `
        <div class="empty-state">
          <p>No encontramos productos disponibles por ahora.</p>
        </div>`;
      return;
    }

    grid.innerHTML = data.map(productCard).join("");

    grid.addEventListener("click", (e) => {
      
      // 1. Revisa si se hizo clic en el 'wrapper' del producto
      const wrapper = e.target.closest(".producto-link-wrapper");
      if (wrapper) {
        e.preventDefault();
        const id = wrapper.dataset.id;
        
        // 🔽 ¡AQUÍ ESTÁ EL CAMBIO! 🔽
        // Usamos '#' en lugar de '?'
        window.location.href = `detalle_producto.html#id=${id}`;
        return; 
      }

      // 2. Revisa si se hizo clic en el botón de "Añadir"
      const btn = e.target.closest(".btn-add-cart");
      if (btn) {
        const id = Number(btn.dataset.id);
        const name = decodeURIComponent(btn.dataset.name || "");
        const price = Number(btn.dataset.price || 0);
        const image = btn.dataset.img || "../Public/imagenes/placeholder.jpg";
        const sku = btn.dataset.sku || null;

        addItem({ id, name, price, image, sku }, 1);

        const prev = btn.textContent;
        btn.textContent = "¡Añadido!";
        btn.disabled = true;
        setTimeout(() => { btn.textContent = prev; btn.disabled = false; }, 900);
        return; 
      }
    });

  } catch (err) {
    console.error("[productos] error:", err);
    grid.innerHTML = `
      <div class="error-state">
        <p>Ups, no pudimos cargar los productos.</p>
        <pre style="white-space:pre-wrap;">${String(err.message || err)}</pre>
      </div>`;
  }
}



document.addEventListener("DOMContentLoaded", loadProducts);