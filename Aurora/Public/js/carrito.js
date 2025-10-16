// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice
} from "./cart.js";
document.addEventListener("click", (e) => {
  if (e.target.id === "btn-mp") {
    console.log("✅ Click detectado en botón Mercado Pago");
  }
});


// === Utilidades ===
// Lee el total tal como se muestra (dataset primero; si no, parsea el texto)
function getDisplayedTotal() {
  const container = document.querySelector("#cart-container");
  const ds = container?.dataset?.total;
  if (ds && !Number.isNaN(Number(ds))) return Number(ds);

  const txt = document.querySelector("#cart-total-txt")?.textContent || "";
  return parseCLP(txt);
}
function parseCLP(texto) {
  // "$12.345" -> 12345
  const n = (texto || "").replace(/[^\d]/g, "");
  return Number(n || 0);
}
// Normaliza precios CLP que pueden venir como "$10.000" o "10.000"
function clpToNumber(v) {
  if (typeof v === "number") return v;
  const n = String(v).replace(/[^\d]/g, ""); // deja sólo dígitos
  return Number(n || 0);
}

// Saca un snapshot de la compra y lo guarda para resultado.html
function snapshotCompra() {
  const cart = getCart();
  const items = cart.map(p => ({
    id: p.id,
    title: p.name || p.title || 'Producto',
    qty: Number(p.qty || p.quantity || 1),
    price: clpToNumber(p.price),            // <— ¡clave!
    image: p.image || p.picture_url || ''
  }));
  const total = items.reduce((a,i) => a + i.price * i.qty, 0);

  localStorage.setItem("ultimaCompra", JSON.stringify({
    id: "ORD-" + Date.now(),
    fecha: new Date().toLocaleString("es-CL"),
    envio: 0,
    total,
    items
  }));
}

// Para pruebas: ir directo al voucher sin pasar por pasarela
function goToResultado() {
  snapshotCompra();
  window.location.href = "./resultado.html";
}

const $ = (s) => document.querySelector(s);

// POST JSON helper (con buen mensaje de error)
async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`HTTP ${r.status} - ${text}`);
  try { return JSON.parse(text); } catch { return {}; }
}

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
    container.dataset.total = "0";
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

  // ÚNICO innerHTML (evita sobrescrituras)
  container.innerHTML = `
    <div class="cart-list">${rows}</div>
    <div class="cart-total">
      <strong>Total: <span id="cart-total-txt">${formatCLP(totalPrice())}</span></strong>
      <div style="margin-top:10px; display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn-sm alt" id="btn-clear">Vaciar carrito</button>
        
        <a class="btn-sm" id="btn-checkout" href="#">Pagar con Webpay</a>
        <a class="btn-sm" id="btn-mp" href="#">Pagar con Mercado Pago</a>
      </div>
    </div>
  `;

  // Guarda también el total crudo para que el handler lo lea exacto
  container.dataset.total = String(Math.round(totalPrice()));

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

  // Botones globales
  $("#btn-clear")?.addEventListener("click", () => {
    saveCart([]);
    renderCart();
  });
  $("#btn-voucher")?.addEventListener("click", (e) => {
  e.preventDefault();
  goToResultado();
});

  // ====== WEBPAY (tu flujo original, solo cambié el texto de restauración del botón) ======
  $("#btn-checkout")?.addEventListener("click", async (e) => {
    e.preventDefault();

    const btn = e.currentTarget;
    const amount = getDisplayedTotal(); // usa EXACTAMENTE el total mostrado

    if (!amount || amount <= 0) {
      alert("Tu carrito está vacío.");
      return;
    }

    btn.setAttribute("disabled", "disabled");
    const oldText = btn.textContent;
    btn.textContent = "Redirigiendo...";

    try {
      const data = await postJSON("http://localhost:3010/webpay/create", {
        amount,
        buyOrder: "ORD-" + Date.now(),
        sessionId: "USR-" + Date.now()
      });

      if (!data?.token || !data?.url) {
        throw new Error("Respuesta inválida del servidor Webpay");
      }

      // Redirige al formulario de Webpay
      window.location.href = `${data.url}?token_ws=${data.token}`;
    } catch (err) {
      console.error("[checkout]", err);
      alert("No se pudo iniciar el pago. Revisa la consola.");
      btn.removeAttribute("disabled");
      btn.textContent = oldText;
    }
  });
 // ====== MERCADO PAGO ======
$("#btn-mp")?.addEventListener("click", async (e) => {
  e.preventDefault();

  const btn = e.currentTarget;
  const amount =
    typeof getDisplayedTotal === "function"
      ? getDisplayedTotal()
      : Number(totalPrice());

  if (!amount || amount <= 0) {
    alert("Tu carrito está vacío.");
    return;
  }

  // Endpoint backend
  const mpUrl =
    document.querySelector("#cart-container")?.dataset?.mercadopago ||
    "http://localhost:3010/mercadopago/create_preference";

  console.log("[MP] Endpoint llamado:", mpUrl);

  // Armar ítems desde el carrito
  const items = getCart().map((p) => ({
    title: p.name || `Producto ${p.id}`,
    unit_price: Math.round(p.price),
    quantity: p.qty,
    currency_id: "CLP",
    picture_url: p.image || undefined
  }));

  // UI feedback
  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Redirigiendo...";

  try {
    const r = await fetch(mpUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items, amount })
    });

    const txt = await r.text();
    if (!r.ok) {
      alert(`Mercado Pago falló:\nHTTP ${r.status}\n${txt.substring(0, 400)}`);
      throw new Error(`HTTP ${r.status} - ${txt}`);
    }

    const data = (() => { try { return JSON.parse(txt); } catch { return {}; } })();

    const next = data.init_point || data.sandbox_init_point ||
  (data.id ? `https://www.mercadopago.cl/checkout/v1/redirect?preference-id=${data.id}` : null);


    if (!next) throw new Error("Respuesta inválida del backend de MP");
    window.location.href = next;

  } catch (err) {
    console.error("[mercadopago]", err);
    btn.removeAttribute("disabled");
    btn.textContent = oldText;
  }
});



 }

document.addEventListener("DOMContentLoaded", renderCart);
