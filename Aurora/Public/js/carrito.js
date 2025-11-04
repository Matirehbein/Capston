// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice, setQty, updateCartBadge // Importamos todo lo necesario
} from "./cart.js";

// Selector (igual)
const $ = (s) => document.querySelector(s);

// --- Funciones de ayuda (MODIFICADA) ---
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
   if (!r.ok) {
        try {
            const errJson = JSON.parse(text);
            throw new Error(errJson.error || `HTTP ${r.status} - ${text}`);
        } catch(e) {
            if (text.includes("<!doctype html")) {
                 throw new Error(`Error ${r.status}: El servidor devolvió HTML en lugar de JSON. Revisa la consola del backend.`);
            }
            throw e;
        }
   }
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
 * --- RENDER CART (Sin cambios) ---
 */
function renderCart() {
  const container = $("#cart-container");
  if (!container) {
    console.error('No existe el contenedor con id="cart-container"');
    return;
  }
  const cart = getCart();
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
}

// --- ▼▼▼ FUNCIÓN DE PAGO WEBPAY (CORREGIDA) ▼▼▼ ---
async function handleWebpayCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
    alert("Tu carrito está vacío."); return;
  }

  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Preparando pedido...";

  let id_pedido_nuevo;

  // --- PASO 1: Crear el Pedido en app.py (Flask) ---
  try {
    const cartItems = getCart();
    const currentSubtotal = totalPrice();
    const ivaCalculado = calculateIVA(currentSubtotal);

    if (!cartItems || cartItems.length === 0) {
        alert("Error: Carrito vacío.");
        btn.removeAttribute("disabled"); btn.textContent = oldText;
        return;
    }
    
    const pedidoParaCrear = {
      subtotal: currentSubtotal,
      iva: ivaCalculado,
      total: amount,
      items: cartItems.map(item => ({ 
          sku: item.sku,
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          stock: item.stock
      }))
    };

    localStorage.setItem('ultimaCompra', JSON.stringify({
        id: "PENDIENTE-" + Date.now(),
        fecha: new Date().toLocaleString('es-CL'),
        ...pedidoParaCrear,
        // Guardar explícitamente los items con nombre/imagen
        items: cartItems.map(item => ({ 
            sku: item.sku,
            title: item.name || 'Producto Sin Nombre',
            qty: Number(item.qty) || 1,
            price: Number(item.price) || 0,
            image: item.image || '',
            variation: item.variation,
            stock: item.stock
        }))
    }));

    // Llamar a Flask (app.py)
    const respPedido = await fetch("http://localhost:5000/api/crear-pedido", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(pedidoParaCrear) 
    });

    const respText = await respPedido.text();
    if (!respPedido.ok) {
        try {
            const errJson = JSON.parse(respText);
            throw new Error(errJson.error || "Error desconocido del backend");
        } catch (e) {
            if (respText.includes("<!doctype html")) {
                 throw new Error(`Error ${respPedido.status}: El servidor devolvió HTML (¿No logueado o ruta no encontrada?)`);
            }
            throw new Error(`HTTP ${respPedido.status}: ${respText}`);
        }
    }
    
    const dataPedido = JSON.parse(respText);
    if (!dataPedido.id_pedido) {
        throw new Error("El backend no devolvió un id_pedido.");
    }
    
    id_pedido_nuevo = dataPedido.id_pedido;
    console.log("Pedido creado con ID:", id_pedido_nuevo);
    
    const compraGuardada = JSON.parse(localStorage.getItem('ultimaCompra') || '{}');
    compraGuardada.id = id_pedido_nuevo;
    localStorage.setItem('ultimaCompra', JSON.stringify(compraGuardada));

  } catch (error) {
      console.error("Error en Paso 1 (Crear Pedido en app.py):", error);
      alert(`Hubo un problema al crear tu pedido: ${error.message}. ¿Iniciaste sesión?`);
      btn.removeAttribute("disabled"); btn.textContent = oldText;
      localStorage.removeItem('ultimaCompra');
      return;
  }
  // --- FIN PASO 1 ---

  // --- PASO 2: Iniciar Pago en webpay.js (Node) ---
  btn.textContent = "Redirigiendo...";
  try {
    const sessionIdWebpay = "USR-" + Date.now();

    const data = await postJSON("http://localhost:3010/webpay/create", {
      amount: amount, 
      buyOrder: id_pedido_nuevo, 
      sessionId: sessionIdWebpay
    });

    if (!data?.token || !data?.url) throw new Error("Respuesta inválida del servidor Webpay");

    window.location.href = `${data.url}?token_ws=${data.token}`;

  } catch (err) {
    console.error("[checkout Webpay]", err);
    alert("No se pudo iniciar el pago con Webpay. Revisa la consola.");
    btn.removeAttribute("disabled"); btn.textContent = oldText;
  }
}
// --- FIN FUNCIÓN WEBPAY ---

// --- ▼▼▼ FUNCIÓN DE PAGO MERCADOPAGO (CORREGIDA) ▼▼▼ ---
async function handleMercadoPagoCheckout(btn) {
  const amount = getDisplayedTotal();
  if (!amount || amount <= 0) {
      alert("Tu carrito está vacío."); return;
  }

  btn.setAttribute("disabled", "disabled");
  const oldText = btn.textContent;
  btn.textContent = "Preparando pedido...";

  let id_pedido_nuevo;

  // --- PASO 1: Crear el Pedido en app.py (Flask) ---
  try {
    const cartItems = getCart();
    const currentSubtotal = totalPrice();
    const ivaCalculado = calculateIVA(currentSubtotal);

    if (!cartItems || cartItems.length === 0) {
        alert("Error: Carrito vacío.");
        btn.removeAttribute("disabled"); btn.textContent = oldText;
        return;
    }
    
    const pedidoParaCrear = {
      subtotal: currentSubtotal,
      iva: ivaCalculado,
      total: amount,
      items: cartItems.map(item => ({ 
          sku: item.sku,
          qty: Number(item.qty) || 1,
          price: Number(item.price) || 0,
          stock: item.stock
      }))
    };

    // --- ▼▼▼ ¡CORRECCIÓN! Usar el mapeo completo para guardar los detalles ▼▼▼ ---
    localStorage.setItem('ultimaCompra', JSON.stringify({
        id: "PENDIENTE-MP-" + Date.now(),
        fecha: new Date().toLocaleString('es-CL'),
        subtotal: currentSubtotal,
        iva: ivaCalculado,
        total: amount,
        envio: 0,
        items: cartItems.map(item => ({ 
            sku: item.sku,
            title: item.name || 'Producto Sin Nombre', // <--- ESTO ES LO QUE ARREGLA EL ERROR
            qty: Number(item.qty) || 1,
            price: Number(item.price) || 0,
            image: item.image || '',
            variation: item.variation,
            stock: item.stock
        }))
    }));
    // --- ▲▲▲ FIN CORRECCIÓN ▲▲▲ ---

    const respPedido = await fetch("http://localhost:5000/api/crear-pedido", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(pedidoParaCrear)
    });

    const respText = await respPedido.text();
    if (!respPedido.ok) {
        try {
            const errJson = JSON.parse(respText);
            throw new Error(errJson.error || "Error desconocido del backend");
        } catch (e) {
            if (respText.includes("<!doctype html")) {
                 throw new Error(`Error ${respPedido.status}: El servidor devolvió HTML (¿No logueado o ruta no encontrada?)`);
            }
            throw new Error(`HTTP ${respPedido.status}: ${respText}`);
        }
    }
    
    const dataPedido = JSON.parse(respText);

    if (!dataPedido.id_pedido) {
        throw new Error("El backend no devolvió un id_pedido.");
    }
    
    id_pedido_nuevo = dataPedido.id_pedido;
    console.log("Pedido (MP) creado con ID:", id_pedido_nuevo);
    
    const compraGuardada = JSON.parse(localStorage.getItem('ultimaCompra') || '{}');
    compraGuardada.id = id_pedido_nuevo;
    localStorage.setItem('ultimaCompra', JSON.stringify(compraGuardada));

  } catch (error) {
      console.error("Error en Paso 1 (Crear Pedido en app.py):", error);
      alert(`Hubo un problema al crear tu pedido: ${error.message}. ¿Iniciaste sesión?`);
      btn.removeAttribute("disabled"); btn.textContent = oldText;
      localStorage.removeItem('ultimaCompra');
      return;
  }
  // --- FIN PASO 1 ---

  // --- PASO 2: Iniciar Pago en Mercado Pago ---
  btn.textContent = "Redirigiendo...";
  
  const mpUrl = $("#cart-container")?.dataset?.mercadopago || "http://localhost:3010/mercadopago/create_preference";
  
  const itemsForMp = getCart().map((p) => ({
      id: p.sku,
      title: `${p.name} (Talla: ${p.variation?.talla || 'Única'})`,
      unit_price: Math.round(p.price),
      quantity: Number(p.qty) || 1,
      currency_id: "CLP",
      picture_url: p.image || undefined
  }));

  try {
      const r = await fetch(mpUrl, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
              items: itemsForMp, 
              amount: amount,
              external_reference: id_pedido_nuevo
          })
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
// --- FIN FUNCIÓN MERCADOPAGO ---


// --- ▼▼▼ SECCIÓN DE LISTENERS (Sin cambios) ▼▼▼ ---
document.addEventListener("DOMContentLoaded", () => {
    // 1. Dibuja el carrito inicial
    renderCart();

    // 2. Añade UN SOLO listener de clics al contenedor
    const container = $("#cart-container");
    if (container) {
        container.addEventListener("click", (e) => {
            const target = e.target;
    
            // Lógica de botones +/- (CORREGIDA)
            if (target.classList.contains("qty-btn")) {
              const sku = target.dataset.sku;
              const action = target.dataset.action;
              const item = getCart().find(it => it.sku === sku);
              if (!item) return;
        
              let currentQty = parseInt(item.qty, 10);
              if (isNaN(currentQty) || currentQty < 1) {
                  currentQty = 1;
              }
        
              let newQty = currentQty;
        
              if (action === "inc") {
                  const maxStock = parseInt(item.stock, 10); 
                  const limit = (!isNaN(maxStock) && maxStock > 0) ? maxStock : 10; 
                  
                  if (currentQty < limit) {
                      newQty = currentQty + 1;
                  } else {
                      newQty = limit;
                      alert(`Has alcanzado el límite de stock (${limit} unidades) para este producto.`);
                  }
                  if (isNaN(maxStock)) {
                      console.warn(`No se encontró 'item.stock' para ${sku}. Usando límite de 10.`);
                  }

              } else if (action === "dec") {
                  if (currentQty > 1) {
                      newQty = currentQty - 1;
                  } else {
                      newQty = 1; // Mínimo 1
                  }
              }
              
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
              handleWebpayCheckout(target);
            }
            if (target.id === "btn-mp") {
              e.preventDefault();
              handleMercadoPagoCheckout(target);
            }
        });
    }
});

// Vuelve a renderizar si el localStorage cambia
window.addEventListener("storage", renderCart);
// --- ▲▲▲ FIN SECCIÓN MODIFICADA ▲▲▲ ---
