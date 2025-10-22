// ../Public/js/cart.js

export const STORAGE_KEY = "aurora_cart_v1";
const API_BASE = "http://localhost:5000"; // Asegúrate que esta línea existe

/**
 * --- VERSIÓN CORREGIDA ---
 * Formatea un número como moneda Chilena (CLP).
 */
export function formatCLP(value) {
  // Intenta convertir directamente a número. Si falla, intenta limpiar puntos.
  let numberValue = Number(value);
  if (isNaN(numberValue)) {
      // console.warn(`formatCLP recibió un valor no numérico directo: ${value}`);
      const cleanedValue = Number(String(value).replace(/\./g, '').replace(/,/g, '.'));
      if (!isNaN(cleanedValue)) {
          numberValue = cleanedValue;
      } else {
          // console.warn(`formatCLP no pudo limpiar el valor: ${value}`);
          numberValue = 0; // Fallback final
      }
  } else {
      value = numberValue;
  }
  try {
    return value.toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0
    });
  } catch (e) {
    console.error("Error formateando CLP:", e);
    return `$${Math.round(value)}`;
  }
}

/**
 * Obtiene el carrito desde localStorage.
 */
export function getCart() {
  try {
    const cartData = localStorage.getItem(STORAGE_KEY);
    return cartData ? JSON.parse(cartData) : [];
  } catch {
    console.error("Error al leer el carrito de localStorage.");
    return [];
  }
}

/**
 * Guarda el carrito en localStorage.
 */
export function saveCart(cart) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    window.dispatchEvent(new Event('storage'));
  } catch (e) {
    console.error("Error al guardar el carrito en localStorage:", e);
  }
}

/**
 * --- addItem MODIFICADO ---
 * Llama a 'openAddedToCartModal' después de añadir.
 */
export function addItem(product, qty = 1) {
  const cart = getCart();
  const quantityToAdd = Number(qty) || 1;
  const existingItemIndex = cart.findIndex(it => it.sku === product.sku);
  let itemAddedOrUpdated;
  if (existingItemIndex > -1) {
    cart[existingItemIndex].qty += quantityToAdd;
    itemAddedOrUpdated = cart[existingItemIndex];
  } else {
    const newItem = {
      id: product.id, sku: product.sku, name: product.name,
      price: Number(product.price) || 0, image: product.image || "../Public/imagenes/placeholder.jpg",
      variation: product.variation || { talla: 'Única', color: '' }, qty: quantityToAdd
    };
    cart.push(newItem); itemAddedOrUpdated = newItem;
  }
  saveCart(cart);
  updateCartBadge();

  // --- LLAMADA AL MODAL ---
  console.log("addItem: Llamando a openAddedToCartModal..."); // DEBUG
  if (typeof openAddedToCartModal === 'function') {
      openAddedToCartModal(itemAddedOrUpdated, quantityToAdd);
  } else {
      console.error("¡ERROR! La función openAddedToCartModal no está definida. Revisa que esté en cart.js y no dentro de otra función."); // DEBUG
  }
  return cart;
}

export function removeItem(sku) { let c = getCart().filter(i=>i.sku!==sku); saveCart(c); updateCartBadge(); return c;}
export function setQty(sku, qty) { const c=getCart(); const i=c.findIndex(it=>it.sku===sku); if(i>-1){ const n=Math.max(0,Number(qty)||0); if(n===0){c.splice(i,1);}else{c[i].qty=n;} saveCart(c); updateCartBadge();} return c;}
export function totalItems() { return getCart().reduce((a, i) => a + (Number(i.qty) || 0), 0); }
export function totalPrice() { return getCart().reduce((a, i) => a + ((Number(i.qty) || 0) * (Number(i.price) || 0)), 0); }
export function updateCartBadge() { const t=totalItems(); document.querySelectorAll(".icon-cart").forEach(ic=>{let b=ic.querySelector(".cart-badge");if(!b){b=document.createElement("span");b.className="cart-badge";b.style.cssText="position:absolute;top:-8px;right:-10px;background-color:var(--color-primary, red);color:white;border-radius:50%;min-width:20px;height:20px;padding:0 4px;font-size:12px;display:flex;align-items:center;justify-content:center;line-height:1;box-sizing:border-box;";ic.style.position='relative';ic.appendChild(b);} if(t>0){b.textContent=t;b.style.display="flex";}else{b.style.display="none";}}); }

document.addEventListener('DOMContentLoaded', updateCartBadge);
window.addEventListener('storage', updateCartBadge);


// --- ▼▼▼ FUNCIÓN PARA ABRIR Y POBLAR EL MODAL (CON DEBUG LOGS) ▼▼▼ ---
async function openAddedToCartModal(item, quantityAdded) {
  console.log("openAddedToCartModal: Iniciando..."); // DEBUG
  const modal = document.getElementById('added-to-cart-modal');
  console.log("openAddedToCartModal: Elemento modal encontrado:", modal); // DEBUG
  if (!modal) {
      console.error("¡ERROR CRÍTICO! No se encontró el DIV principal del modal con id='added-to-cart-modal'. Verifica el HTML.");
      return;
  }

  // Rellenar detalles
  const itemImg = document.getElementById('modal-item-img');       if(itemImg) itemImg.src = item.image; else console.warn("ID 'modal-item-img' no encontrado");
  const itemName = document.getElementById('modal-item-name');     if(itemName) itemName.textContent = item.name; else console.warn("ID 'modal-item-name' no encontrado");
  const itemPrice = document.getElementById('modal-item-price');    if(itemPrice) itemPrice.textContent = formatCLP(item.price); else console.warn("ID 'modal-item-price' no encontrado");
  const itemColor = document.getElementById('modal-item-color');    if(itemColor) itemColor.textContent = item.variation?.color || 'N/A'; else console.warn("ID 'modal-item-color' no encontrado");
  const itemSize = document.getElementById('modal-item-size');      if(itemSize) itemSize.textContent = item.variation?.talla || 'Única'; else console.warn("ID 'modal-item-size' no encontrado");
  const itemQty = document.getElementById('modal-item-qty');        if(itemQty) itemQty.textContent = quantityAdded; else console.warn("ID 'modal-item-qty' no encontrado");

  // Rellenar resumen
  const cartCount = document.getElementById('modal-cart-count');     if(cartCount) cartCount.textContent = totalItems(); else console.warn("ID 'modal-cart-count' no encontrado");
  const cartSubtotal = document.getElementById('modal-cart-subtotal'); if(cartSubtotal) cartSubtotal.textContent = formatCLP(totalPrice()); else console.warn("ID 'modal-cart-subtotal' no encontrado");
  const cartTotal = document.getElementById('modal-cart-total');       if(cartTotal) cartTotal.textContent = formatCLP(totalPrice()); else console.warn("ID 'modal-cart-total' no encontrado");

  // Mostrar el modal
  console.log("openAddedToCartModal: Intentando añadir clase 'visible'..."); // DEBUG
  modal.classList.add('visible');
  console.log("openAddedToCartModal: Clase 'visible' añadida. ¿Se ve el modal?"); // DEBUG

  // Cargar recomendaciones
  const recoGrid = document.getElementById('modal-recommendations-grid');
  const recoLoading = document.getElementById('modal-reco-loading');
  if (!recoGrid || !recoLoading) {
      console.error("Elementos de recomendaciones no encontrados.");
      const recoSection = document.querySelector('.recommendations-section');
      if (recoSection) recoSection.style.display = 'none';
  } else {
      recoGrid.innerHTML = ''; recoLoading.style.display = 'block';
      try {
        const itemColor = item.variation?.color;
        if (itemColor && String(itemColor).trim() !== '' && String(itemColor).toLowerCase() !== 'n/a') {
          const recoUrl = `${API_BASE}/api/productos_por_color?color=${encodeURIComponent(itemColor)}&exclude_id=${item.id}`;
          const res = await fetch(recoUrl);
          if (res.ok) {
            const recommendations = await res.json();
            if(recoLoading) recoLoading.style.display = 'none';
            if (recommendations.length > 0) {
              recoGrid.innerHTML = recommendations.map(reco => `
                <a href="detalle_producto.html#id=${reco.id_producto}" class="recommendation-item">
                  <img src="${reco.imagen_url || '../Public/imagenes/placeholder.jpg'}" alt="${reco.nombre_producto}" loading="lazy">
                  <p>${reco.nombre_producto}</p>
                  <p><strong>${formatCLP(reco.precio_producto)}</strong></p>
                </a>
              `).join('');
            } else { recoGrid.innerHTML = '<p style="grid-column: 1 / -1; text-align: center; color: #888;">No hay recomendaciones por ahora.</p>'; }
          } else { const errorText = await res.text(); console.error("Error API reco:", res.status, errorText); throw new Error(`Error ${res.status}`); }
        } else { if(recoLoading) recoLoading.style.display = 'none'; recoGrid.innerHTML = '<p style="grid-column: 1 / -1; text-align: center; color: #888;">No se pudo det. color.</p>'; }
      } catch (error) { console.error("Error cargando reco:", error); if(recoLoading) recoLoading.style.display = 'none'; recoGrid.innerHTML = '<p style="grid-column: 1 / -1; text-align: center; color: #d9534f;">Error al cargar reco.</p>'; }
  }

  // Listeners para cerrar
  const closeBtn = document.getElementById('modal-close-btn');
  const continueBtn = document.getElementById('modal-continue-shopping-btn');
  const overlay = document.getElementById('added-to-cart-modal');
  if(closeBtn) closeBtn.onclick = () => { console.log("Cerrando modal (botón X)"); modal.classList.remove('visible'); }; else console.warn("ID 'modal-close-btn' no encontrado");
  if(continueBtn) continueBtn.onclick = () => { console.log("Cerrando modal (botón Seguir Comprando)"); modal.classList.remove('visible'); }; else console.warn("ID 'modal-continue-shopping-btn' no encontrado");
  if(overlay) {
      overlay.onclick = (e) => {
          if (e.target === overlay) { console.log("Cerrando modal (click overlay)"); modal.classList.remove('visible'); }
      };
  } else { console.error("Overlay no encontrado para listener.");}
  console.log("openAddedToCartModal: Fin."); // DEBUG
}
// --- ▲▲▲ FIN FUNCIÓN MODAL ▲▲▲ ---