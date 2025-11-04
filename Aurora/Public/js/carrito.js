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

// --- NUEVA FUNCIÓN PARA CALCULAR IVA ---
const IVA_PERCENTAGE = 0.19; // 19% de IVA

function calculateIVA(subtotal) {
  return Math.round(subtotal * IVA_PERCENTAGE);
}
// --- FIN NUEVA FUNCIÓN ---

/**
 * --- RENDER CART (Sin cambios funcionales) ---
 * Esta función AHORA solo dibuja el HTML.
 * Los listeners se movieron a DOMContentLoaded.
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
    const subtotalItem = price * quantity;

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
        <p class="cart-subtotal">${formatCLP(subtotalItem)}</p>
      </div>
    `;
  }).join("");

  const currentSubtotal = totalPrice();
  const ivaCalculado = calculateIVA(currentSubtotal);
  const totalConIVA = currentSubtotal + ivaCalculado;

  // Render HTML completo
  container.innerHTML = `
    <div class="cart-list">${rows}</div>
    <div class="cart-total">
      <p style="text-align: right; margin-bottom: 5px;">Subtotal: ${formatCLP(currentSubtotal)}</p>
      <p style="text-align: right; margin-bottom: 15px;">Impuestos (IVA 19%): ${formatCLP(ivaCalculado)}</p>
      <strong>Total: <span id="cart-total-txt">${formatCLP(totalConIVA)}</span></strong>
      <div style="margin-top:10px; display:flex; gap:8px; justify-content:flex-end;">
        <button class="btn-sm alt" id="btn-clear">Vaciar carrito</button>
        <a class="btn-sm" id="btn-checkout" href="#">Pagar con Webpay</a>
        <a class="btn-sm" id="btn-mp" href="#">Pagar con Mercado Pago</a>
      </div>
    </div>
  `;

  container.dataset.total = String(Math.round(totalConIVA));
  updateCartBadge();

  // --- ¡EL LISTENER FUE MOVIDO FUERA DE ESTA FUNCIÓN! ---
}

// --- FUNCIONES DE PAGO (Sin cambios) ---
async function handleWebpayCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
    alert("Tu carrito está vacío."); return;
  }

  // --- GUARDAR CARRITO ANTES DE PAGAR ---
  try {
    const cartItems = getCart();
    const currentSubtotal = totalPrice();
    const ivaCalculado = calculateIVA(currentSubtotal);
    const totalConIVA = currentSubtotal + ivaCalculado; 

    if (!cartItems || cartItems.length === 0) {
        alert("Error: No se encontraron items en el carrito para guardar.");
        return; 
    }

    const compraParaGuardar = {
      id: "PENDIENTE-" + Date.now(),
      fecha: new Date().toLocaleString('es-CL'),
      subtotal: currentSubtotal,
      iva: ivaCalculado,
      total: totalConIVA,
      envio: 0, 
      items: cartItems.map(item => ({ 
          sku: item.sku,
          title: item.name || 'Producto Sin Nombre',
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          image: item.image || '',
          variation: item.variation,
          stock: item.stock // Guardamos el stock (leído desde detalle_producto.js)
      }))
    };

    localStorage.setItem('ultimaCompra', JSON.stringify(compraParaGuardar));
    console.log("Copia del carrito guardada en 'ultimaCompra'", compraParaGuardar);

  } catch (error) {
      console.error("Error al guardar 'ultimaCompra' en localStorage:", error);
      alert("Hubo un problema al preparar los detalles de la compra. Intenta de nuevo.");
      return;
  }
  // --- FIN GUARDAR CARRITO ---

  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Redirigiendo...";
  try {
    const buyOrderWebpay = "ORD-" + Date.now();
    const sessionIdWebpay = "USR-" + Date.now();

    const data = await postJSON("http://localhost:3010/webpay/create", {
      amount: amount, // total CON IVA
      buyOrder: buyOrderWebpay,
      sessionId: sessionIdWebpay
    });
    if (!data?.token || !data?.url) throw new Error("Respuesta inválida del servidor Webpay");

    window.location.href = `${data.url}?token_ws=${data.token}`;

  } catch (err) {
    console.error("[checkout Webpay]", err);
    alert("No se pudo iniciar el pago con Webpay. Revisa la consola.");
    btn.removeAttribute("disabled"); btn.textContent = oldText;
     localStorage.removeItem('ultimaCompra');
     console.log("'ultimaCompra' eliminada por fallo al iniciar pago.");
  }
}

async function handleMercadoPagoCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
      alert("Tu carrito está vacío."); return;
  }

    // --- GUARDAR CARRITO ANTES DE PAGAR (MP) ---
    try {
    const cartItems = getCart();
    const currentSubtotal = totalPrice();
    const ivaCalculado = calculateIVA(currentSubtotal);
    const totalConIVA = currentSubtotal + ivaCalculado;

    if (!cartItems || cartItems.length === 0) {
        alert("Error: Carrito vacío."); return;
    }
    const compraParaGuardar = {
      id: "PENDIENTE-MP-" + Date.now(),
      fecha: new Date().toLocaleString('es-CL'),
      subtotal: currentSubtotal,
      iva: ivaCalculado,
      total: totalConIVA,
      envio: 0,
      items: cartItems.map(item => ({ 
          sku: item.sku,
          title: item.name || 'Producto Sin Nombre',
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          image: item.image || '',
          variation: item.variation,
          stock: item.stock
       }))
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
      unit_price: Math.round(p.price), // Enviamos precio unitario SIN IVA
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
          body: JSON.stringify({ items: items, amount: amount }) // amount es el total CON IVA
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
      localStorage.removeItem('ultimaCompra');
      console.log("'ultimaCompra' eliminada por fallo al iniciar pago MP.");
  }
}
// --- FIN FUNCIONES DE PAGO ---


// --- ▼▼▼ SECCIÓN MODIFICADA (LISTENERS MOVIDOS AQUÍ) ▼▼▼ ---

// Ejecuta renderCart cuando la página cargue
document.addEventListener("DOMContentLoaded", () => {
    // 1. Dibuja el carrito inicial
    renderCart();

    // 2. Añade UN SOLO listener de clics al contenedor
    // Este listener vivirá por siempre y manejará los clics
    // en los botones, sin importar cuántas veces se re-dibuje el carrito.
    const container = $("#cart-container");
    if (container) {
        container.addEventListener("click", (e) => {
            const target = e.target;
    
            // --- LÓGICA DE BOTONES +/- CORREGIDA ---
            if (target.classList.contains("qty-btn")) {
              const sku = target.dataset.sku;
              const action = target.dataset.action;
              const item = getCart().find(it => it.sku === sku);
              if (!item) return;
        
              // FORZAR A NÚMERO ENTERO
              let currentQty = parseInt(item.qty, 10);
              if (isNaN(currentQty) || currentQty < 1) {
                  currentQty = 1;
              }
        
              let newQty = currentQty;
        
              if (action === "inc") {
                  // LÍMITE DE 10 UNIDADES
                  const maxLimit = 10; 
                  
                  if (currentQty < maxLimit) {
                      newQty = currentQty + 1; // Suma numérica
                  } else {
                      newQty = maxLimit; // No pasar de 10
                      alert(`Puedes agregar un máximo de ${maxLimit} unidades por producto.`);
                  }
              } else if (action === "dec") {
                  // CORRECCIÓN DECREMENTO (Mínimo 1)
                  if (currentQty > 1) {
                      newQty = currentQty - 1; // Resta numérica
                  } else {
                      newQty = 1; // El mínimo es 1
                  }
              }
              
              setQty(sku, newQty); // Guarda la nueva cantidad
              renderCart(); // Re-dibuja
            }
            // --- FIN LÓGICA +/- CORREGIDA ---
    
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
              handleWebpayCheckout(target);
            }
            if (target.id === "btn-mp") {
              e.preventDefault();
              handleMercadoPagoCheckout(target);
            }
        });
    }
});

// Vuelve a renderizar si el localStorage cambia (ej: en otra pestaña)
window.addEventListener("storage", renderCart);
// --- ▲▲▲ FIN SECCIÓN MODIFICADA ▲▲▲ ---