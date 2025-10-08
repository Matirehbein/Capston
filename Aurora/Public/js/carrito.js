// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice
} from "./cart.js";

const $ = (s) => document.querySelector(s);

function renderCart() {
  const container = $("#cart-container");
  if (!container) {
    console.error('No existe el contenedor con id="cart-container"');
    return;
  }

  const cart = getCart();

  // Carrito vacío → renderizamos bloque completo (no usamos .style en nada existente)
  if (!cart.length) {
    container.innerHTML = `
      <div class="cart-empty-box">
        <p>Tu carrito está vacío</p>
        <a href="./productos.html" class="btn-lg">Explorar productos</a>
      </div>
    `;
    return;
  }

  // Render de items + total
  const rows = cart.map((p) => {
    const subtotal = p.price * p.qty;
    return `
      <div class="cart-item" data-id="${p.id}">
        <img class="cart-img" src="${p.image}" alt="${p.name}"
             onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
        <div class="cart-info">
          <h3>${p.name}</h3>
          ${p.sku ? `<p class="sku">SKU: ${p.sku}</p>` : ""}
          <p class="price">${formatCLP(p.price)}</p>
          <div class="cart-actions">
            <button class="qty-btn" data-action="dec">-</button>
            <span class="qty-val">${p.qty}</span>
            <button class="qty-btn" data-action="inc">+</button>
            <button class="remove-btn">Eliminar</button>
          </div>
        </div>
        <p class="cart-subtotal">${formatCLP(subtotal)}</p>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="cart-list">${rows}</div>
    <div class="cart-total">
      <strong>Total: ${formatCLP(totalPrice())}</strong>
      <div style="margin-top:10px; display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn-sm alt" id="btn-clear">Vaciar carrito</button>
        <a class="btn-sm" id="btn-checkout" href="#">Proceder al pago</a>
      </div>
    </div>
  `;

  // Eventos fila (cantidades / eliminar)
  container.querySelectorAll(".cart-item").forEach(row => {
    const id = Number(row.dataset.id);
    row.querySelectorAll(".qty-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.action;
        const cart = getCart();
        const item = cart.find(it => it.id === id);
        if (!item) return;
        if (action === "inc") item.qty += 1;
        if (action === "dec" && item.qty > 1) item.qty -= 1;
        saveCart(cart);
        renderCart();
      });
    });
    row.querySelector(".remove-btn")?.addEventListener("click", () => {
      removeItem(id);
      renderCart();
    });
  });

  // ...todo tu código arriba igual...

  // Botones globales
  $("#btn-clear")?.addEventListener("click", () => {
    saveCart([]);
    renderCart();
  });

  // ⬇⬇⬇ REEMPLAZA este bloque por el de abajo ⬇⬇⬇
  $("#btn-checkout")?.addEventListener("click", async (e) => {
    e.preventDefault();

    const btn = e.currentTarget;
    const amount = Number(totalPrice()); // <-- total dinámico (en CLP)

    if (!amount || amount <= 0) {
      alert("Tu carrito está vacío.");
      return;
    }

    btn.setAttribute("disabled", "disabled");
    btn.textContent = "Redirigiendo...";

    try {
      const r = await fetch("http://localhost:3010/webpay/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount,                               // 👈 usa el total dinámico
          buyOrder: "ORD-" + Date.now(),
          sessionId: "USR-" + Date.now()
        })
      });

      const preview = await r.clone().text();
      if (!r.ok) throw new Error(`HTTP ${r.status} - ${preview}`);

      const data = await r.json();
      if (!data?.token || !data?.url) {
        throw new Error("Respuesta inválida del servidor");
      }

      // Redirige al formulario de Webpay
      window.location.href = `${data.url}?token_ws=${data.token}`;
    } catch (err) {
      console.error("[checkout]", err);
      alert("No se pudo iniciar el pago. Revisa la consola.");
      btn.removeAttribute("disabled");
      btn.textContent = "Proceder al pago";
    }
  });
// ...fin de renderCart()

}
document.addEventListener("DOMContentLoaded", renderCart);
