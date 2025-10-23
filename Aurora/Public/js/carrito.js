// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice, setQty, updateCartBadge // Importamos todo lo necesario
} from "./cart.js";

// Selector (igual)
const $ = (s) => document.querySelector(s);

// --- Funciones de ayuda (las mantengo como las tenías) ---
function parseCLP(texto) {
  const n = (texto || "").replace(/[^\d]/g, "");
  return Number(n || 0);
}
function clpToNumber(v) {
  if (typeof v === "number") return v;
  const n = String(v).replace(/[^\d]/g, "");
  return Number(n || 0);
}
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
function getDisplayedTotal() {
  const container = document.querySelector("#cart-container");
  const ds = container?.dataset?.total;
  if (ds && !Number.isNaN(Number(ds))) return Number(ds);
  const txt = document.querySelector("#cart-total-txt")?.textContent || "";
  return parseCLP(txt);
}
// --- Fin Funciones de ayuda ---


/**
 * --- RENDER CART ADAPTADO A TU HTML ORIGINAL ---
 * Pinta el contenido del carrito usando tu estructura.
 * Muestra SKU y Talla. Usa data-sku.
 */
function renderCart() {
  const container = $("#cart-container");
  if (!container) {
    console.error('No existe el contenedor con id="cart-container"');
    return;
  }

  const cart = getCart();

  // Carrito vacío (tu HTML original)
  if (!cart.length) {
    container.innerHTML = `
      <div class="cart-empty-box">
        <p>Tu carrito está vacío</p>
        <a href="./productos.html" class="btn-lg">Explorar productos</a>
      </div>
    `;
    container.dataset.total = "0";
    updateCartBadge(); // Asegura badge en 0
    return;
  }

  // --- TEMPLATE DE ITEM ADAPTADO ---
  const rows = cart.map((p) => {
    // Aseguramos que qty y price sean números para calcular subtotal
    const quantity = Number(p.qty) || 0;
    const price = Number(p.price) || 0;
    const subtotal = price * quantity;

    return `
      <div class="cart-item" data-sku="${p.sku}"> 
        <img class="cart-img" src="${p.image}" alt="${p.name}"
             onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
        <div class="cart-info">
          <h3>${p.name}</h3>
          
          <p style="font-size: 0.85em; color: #555; margin: 2px 0;">
             SKU: ${p.sku} <br/> 
             Talla: ${p.variation?.talla || 'Única'} 
          </p>

          <p class="price">${formatCLP(p.price)}</p>
          
          <div class="cart-actions">
            <button class="qty-btn" data-action="dec" data-sku="${p.sku}">-</button>
            <span class="qty-val">${quantity}</span>
            <button class="qty-btn" data-action="inc" data-sku="${p.sku}">+</button>
            <button class="remove-btn" data-sku="${p.sku}">Eliminar</button>
          </div>
        </div>
        <p class="cart-subtotal">${formatCLP(subtotal)}</p>
      </div>
    `;
  }).join("");
  // --- FIN TEMPLATE ADAPTADO ---

  const currentTotal = totalPrice(); // Total real del carrito

  // Render HTML completo (tu estructura original)
  container.innerHTML = `
    <div class="cart-list">${rows}</div>
    <div class="cart-total">
      <strong>Total: <span id="cart-total-txt">${formatCLP(currentTotal)}</span></strong>
      <div style="margin-top:10px; display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn-sm alt" id="btn-clear">Vaciar carrito</button>
        <a class="btn-sm" id="btn-checkout" href="#">Pagar con Webpay</a>
        <a class="btn-sm" id="btn-mp" href="#">Pagar con Mercado Pago</a>
      </div>
    </div>
  `;

  // Guarda el total crudo (sin cambios)
  container.dataset.total = String(Math.round(currentTotal));

  // Actualiza la insignia del header (importante)
  updateCartBadge();

  // --- LISTENERS ADAPTADOS A TU ESTRUCTURA (Usando delegación) ---
  container.addEventListener("click", (e) => {
    const target = e.target;

    // Botón de cantidad (+ o -)
    if (target.classList.contains("qty-btn")) {
      const sku = target.dataset.sku;
      const action = target.dataset.action;
      const item = getCart().find(it => it.sku === sku); // Encuentra el item actual
      if (!item) return;

      let newQty = Number(item.qty) || 0; // Asegura que sea número
      if (action === "inc") {
        newQty++;
      } else if (action === "dec") {
        newQty--;
      }
      
      setQty(sku, newQty); // setQty maneja qty=0 (eliminar)
      renderCart(); // Re-renderiza
    }

    // Botón Eliminar
    if (target.classList.contains("remove-btn")) {
      const sku = target.dataset.sku;
      // Puedes añadir un confirm aquí si quieres
      // if (confirm(`¿Eliminar ${sku}?`)) {
          removeItem(sku);
          renderCart();
      // }
    }

    // Botón Vaciar Carrito
    if (target.id === "btn-clear") {
      // Puedes añadir un confirm aquí si quieres
      // if (confirm("¿Vaciar carrito?")) {
          saveCart([]);
          renderCart();
      // }
    }

    // Botones de Pago (llaman a tus funciones originales)
    if (target.id === "btn-checkout") {
      e.preventDefault();
      handleWebpayCheckout(target); 
    }
    if (target.id === "btn-mp") {
         e.preventDefault();
         handleMercadoPagoCheckout(target); 
    }
  });
  // --- FIN LISTENERS ADAPTADOS ---
}

// --- FUNCIONES DE PAGO (Las mantengo como las tenías) ---
async function handleWebpayCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
    alert("Tu carrito está vacío."); return;
  }
  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Redirigiendo...";
  try {
    const data = await postJSON("http://localhost:3010/webpay/create", {
      amount, buyOrder: "ORD-" + Date.now(), sessionId: "USR-" + Date.now()
    });
    if (!data?.token || !data?.url) throw new Error("Respuesta inválida del servidor Webpay");
    window.location.href = `${data.url}?token_ws=${data.token}`;
  } catch (err) {
    console.error("[checkout Webpay]", err);
    alert("No se pudo iniciar el pago con Webpay. Revisa la consola.");
    btn.removeAttribute("disabled"); btn.textContent = oldText;
  }
}

async function handleMercadoPagoCheckout(btn) {
    const amount = getDisplayedTotal();
    if (!amount || amount <= 0) {
        alert("Tu carrito está vacío."); return;
    }
    
    const mpUrl =
  document.querySelector("#cart-container")?.dataset?.mercadopago ||
  "http://localhost:3010/api/mercadopago/create";  // ← con /api


const items = getCart().map(p => ({
  id: String(p.sku),
  title: `${p.name} (Talla: ${p.variation?.talla || 'Única'})`,
  unit_price: Math.max(1, Math.round(Number(String(p.price).replace(/[^\d.-]/g, '')) || 0)),
  quantity: Math.max(1, Number(p.qty) || 1),
  currency_id: 'CLP',
  picture_url: p.image || undefined
}));
await fetch('http://localhost:3010/api/mercadopago/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ items })
});

    btn.setAttribute("disabled", "disabled");
    const oldText = btn.textContent;
    btn.textContent = "Redirigiendo...";
    try {
        const r = await fetch(mpUrl, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items, amount }) 
        });
        const txt = await r.text();
        if (!r.ok) {
            alert(`Mercado Pago falló:\nHTTP ${r.status}\n${txt.substring(0, 400)}`);
            throw new Error(`HTTP ${r.status} - ${txt}`);
        }
        const data = (() => { try { return JSON.parse(txt); } catch { return {}; } })();
        const next = data.init_point || data.sandbox_init_point || (data.id ? `https://www.mercadopago.cl/checkout/v1/redirect?preference-id=${data.id}` : null);
        if (!next) throw new Error("Respuesta inválida del backend de MP");
        window.location.href = next;
    } catch (err) {
        console.error("[checkout Mercado Pago]", err);
        alert("No se pudo iniciar el pago con Mercado Pago. Revisa la consola.");
        btn.removeAttribute("disabled"); btn.textContent = oldText;
    }
}
// --- FIN FUNCIONES DE PAGO ---


// Ejecuta renderCart cuando la página cargue
document.addEventListener("DOMContentLoaded", renderCart);

