// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice, setQty, updateCartBadge // Importamos todo lo necesario
} from "./cart.js";

// Selector (igual)
const $ = (s) => document.querySelector(s);

// --- Funciones de ayuda (sin cambios) ---
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
 * --- RENDER CART (Sin cambios funcionales, solo formato) ---
 */
function renderCart() {
  const container = $("#cart-container");
  if (!container) {
    console.error('No existe el contenedor con id="cart-container"');
    return;
  }

  const cart = getCart();

  // Carrito vacío
  if (!cart.length) {
    container.innerHTML = `
      <div class="cart-empty-box">
        <p>Tu carrito está vacío</p>
        <a href="./productos.html" class="btn-lg">Explorar productos</a>
      </div>
    `;
    container.dataset.total = "0";
    updateCartBadge();
    return;
  }

  // Template de item
  const rows = cart.map((p) => {
    const quantity = Number(p.qty) || 0;
    const price = Number(p.price) || 0;
    const subtotal = price * quantity;

    return `
      <div class="cart-item" data-sku="${p.sku}">
        <img class="cart-img" src="${p.image}" alt="${p.name}"
             onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
        <div class="cart-info">
          <h3>${p.name || 'Producto'}</h3>
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

  const currentTotal = totalPrice();

  // Render HTML completo
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

  container.dataset.total = String(Math.round(currentTotal));
  updateCartBadge();

  // Listeners (delegación)
  container.addEventListener("click", (e) => {
    const target = e.target;

    // Botón cantidad (+/-)
    if (target.classList.contains("qty-btn")) {
      const sku = target.dataset.sku;
      const action = target.dataset.action;
      const item = getCart().find(it => it.sku === sku);
      if (!item) return;
      let newQty = Number(item.qty) || 0;
      newQty = action === "inc" ? newQty + 1 : newQty - 1;
      setQty(sku, newQty);
      renderCart();
    }

    // Botón Eliminar
    if (target.classList.contains("remove-btn")) {
      const sku = target.dataset.sku;
      removeItem(sku);
      renderCart();
    }

    // Botón Vaciar Carrito
    if (target.id === "btn-clear") {
      saveCart([]);
      renderCart();
    }

    // Botones de Pago
    if (target.id === "btn-checkout") {
      e.preventDefault();
      handleWebpayCheckout(target); // Llama a la función modificada
    }
    if (target.id === "btn-mp") {
      e.preventDefault();
      handleMercadoPagoCheckout(target);
    }
  });
}

// --- FUNCIONES DE PAGO ---
async function handleWebpayCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
    alert("Tu carrito está vacío."); return;
  }

  // --- ▼▼▼ GUARDAR CARRITO ANTES DE PAGAR ▼▼▼ ---
  try {
    const cartItems = getCart(); // Obtener los items actuales del carrito
    if (!cartItems || cartItems.length === 0) {
        alert("Error: No se encontraron items en el carrito para guardar.");
        return; // No continuar si no hay items
    }

    // Crear el objeto a guardar
    const compraParaGuardar = {
      id: "PENDIENTE-" + Date.now(), // ID temporal
      fecha: new Date().toLocaleString('es-CL'),
      total: amount, // Usamos el total ya calculado para Webpay
      envio: 0, // Ajusta esto si calculas envío en el carrito
      items: cartItems.map(item => ({ // Mapeo explícito para asegurar formato
          sku: item.sku,
          title: item.name || 'Producto Sin Nombre', // Asegura que 'title' exista
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          image: item.image || '',
          variation: item.variation // Guardar variación si la usas
      }))
    };

    // Guardar en localStorage
    localStorage.setItem('ultimaCompra', JSON.stringify(compraParaGuardar));
    console.log("Copia del carrito guardada en 'ultimaCompra'", compraParaGuardar); // Log para confirmar

  } catch (error) {
      console.error("Error al guardar 'ultimaCompra' en localStorage:", error);
      alert("Hubo un problema al preparar los detalles de la compra. Intenta de nuevo.");
      // Detenemos el proceso si no se pudo guardar
      return;
  }
  // --- ▲▲▲ FIN GUARDAR CARRITO ▲▲▲ ---

  // --- Continuar con la lógica de Webpay ---
  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Redirigiendo...";
  try {
    const buyOrderWebpay = "ORD-" + Date.now(); // Orden de compra para esta transacción
    const sessionIdWebpay = "USR-" + Date.now();

    const data = await postJSON("http://localhost:3010/webpay/create", {
      amount,
      buyOrder: buyOrderWebpay,
      sessionId: sessionIdWebpay
    });
    if (!data?.token || !data?.url) throw new Error("Respuesta inválida del servidor Webpay");

    // Redirigir a Webpay
    window.location.href = `${data.url}?token_ws=${data.token}`;

  } catch (err) {
    console.error("[checkout Webpay]", err);
    alert("No se pudo iniciar el pago con Webpay. Revisa la consola.");
    btn.removeAttribute("disabled"); btn.textContent = oldText;
     // Si falla el inicio, es buena idea borrar la 'ultimaCompra' para evitar inconsistencias
     localStorage.removeItem('ultimaCompra');
     console.log("'ultimaCompra' eliminada por fallo al iniciar pago.");
  }
}

async function handleMercadoPagoCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
      alert("Tu carrito está vacío."); return;
  }

   // --- GUARDAR CARRITO ANTES DE PAGAR (TAMBIÉN PARA MERCADOPAGO) ---
   try {
    const cartItems = getCart();
    if (!cartItems || cartItems.length === 0) {
        alert("Error: Carrito vacío."); return;
    }
    const compraParaGuardar = { /* ... (mismo objeto que en Webpay) ... */
      id: "PENDIENTE-MP-" + Date.now(),
      fecha: new Date().toLocaleString('es-CL'),
      total: amount,
      envio: 0,
      items: cartItems.map(item => ({ /* ... mapeo ... */ }))
    };
    localStorage.setItem('ultimaCompra', JSON.stringify(compraParaGuardar));
    console.log("Copia del carrito guardada en 'ultimaCompra' (para MP)", compraParaGuardar);
  } catch (error) {
      console.error("Error al guardar 'ultimaCompra' (para MP):", error);
      alert("Hubo un problema al preparar detalles. Intenta de nuevo.");
      return;
  }
  // --- FIN GUARDAR CARRITO ---

  const mpUrl = $("#cart-container")?.dataset?.mercadopago || "http://localhost:3010/mercadopago/create_preference";
  const items = getCart().map((p) => ({
      id: p.sku,
      title: `${p.name} (Talla: ${p.variation?.talla || 'Única'})`,
      unit_price: Math.round(p.price),
      quantity: Number(p.qty) || 1,
      currency_id: "CLP",
      picture_url: p.image || undefined
  }));

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
      // Borrar 'ultimaCompra' si falla
      localStorage.removeItem('ultimaCompra');
      console.log("'ultimaCompra' eliminada por fallo al iniciar pago MP.");
  }
}
// --- FIN FUNCIONES DE PAGO ---

// Ejecuta renderCart cuando la página cargue
document.addEventListener("DOMContentLoaded", renderCart);

// Vuelve a renderizar si el localStorage cambia
window.addEventListener("storage", renderCart);