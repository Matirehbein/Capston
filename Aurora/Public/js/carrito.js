// ../Public/js/carrito.js
import {
  getCart, saveCart, formatCLP, removeItem, totalPrice, setQty, updateCartBadge
} from "./cart.js";
import { getActiveBranchId } from "./geolocation.js";

const $ = (s) => document.querySelector(s);

// Variable global para el costo de envío actual
let costoEnvioActual = 0;
const IVA_PERCENTAGE = 0.19;

// --- Funciones de Ayuda ---
function calculateIVA(subtotal) { return Math.round(subtotal * IVA_PERCENTAGE); }
function parseCLP(texto) { return Number((texto || "").replace(/[^\d]/g, "")) || 0; }

// Función auxiliar para obtener el total mostrado en pantalla (limpio)
function getDisplayedTotal() {
  const container = document.querySelector("#totals-container");
  const ds = container?.dataset?.total;
  if (ds && !Number.isNaN(Number(ds))) return Number(ds);
  const txt = document.querySelector("#cart-total-txt")?.textContent || "";
  return parseCLP(txt);
}

async function postJSON(url, body) {
   const r = await fetch(url, {
     method: "POST",
     headers: { "Content-Type": "application/json" },
     credentials: 'include',
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
            throw new Error(`HTTP ${r.status}: ${text}`);
        }
   }
   try { return JSON.parse(text); } catch { return {}; }
}

// --- 1. INICIALIZACIÓN Y LOGICA DE ENVIO ---
document.addEventListener('DOMContentLoaded', () => {
    renderCart(); // Renderiza items y totales iniciales
    initShippingLogic(); // Configura fechas y listeners de envío
});

function initShippingLogic() {
    // 1. Calendario Retiro (Flatpickr)
    const fechaMinima = new Date();
    fechaMinima.setDate(fechaMinima.getDate() + 2); // +2 días

    if(window.flatpickr) {
        flatpickr("#retiro_fecha", {
            locale: "es",
            minDate: fechaMinima,
            dateFormat: "Y-m-d",
            disable: [ function(date) { return (date.getDay() === 0); } ] // Domingo cerrado
        });
    }

    // 2. Cargar Sucursales Retiro
    cargarSucursalesRetiro();

    // 3. Calcular Fecha Despacho (7 días hábiles)
    calcularFechaDespacho();

    // 4. Listeners de Radio Buttons (Retiro vs Despacho)
    const radios = document.querySelectorAll('input[name="tipo_entrega"]');
    radios.forEach(radio => {
        radio.addEventListener('change', toggleShippingForm);
    });

    // 5. Listener de Región (Escucha el evento disparado desde el HTML)
    window.addEventListener('regionChanged', (e) => {
        const regionName = e.detail;
        calcularCostoEnvio(regionName);
    });
}

function toggleShippingForm() {
    const radioChecked = document.querySelector('input[name="tipo_entrega"]:checked');
    if (!radioChecked) return;

    const tipo = radioChecked.value;
    const formRetiro = $("#form-retiro");
    const formDespacho = $("#form-despacho");

    if (tipo === 'retiro') {
        formRetiro.style.display = 'block';
        formDespacho.style.display = 'none';
        costoEnvioActual = 0;
    } else {
        formRetiro.style.display = 'none';
        formDespacho.style.display = 'block';
        // Recalcular envío basado en la selección actual
        const regionSelect = $("#select-region");
        calcularCostoEnvio(regionSelect ? regionSelect.value : "");
    }
    updateTotalsDisplay(); // Actualizar totales en pantalla
}

function calcularCostoEnvio(regionName) {
    if (!regionName) {
        costoEnvioActual = 0;
    } else {
        const nombreUpper = regionName.toUpperCase();
        if (nombreUpper.includes("METROPOLITANA") || nombreUpper.includes("SANTIAGO")) {
            costoEnvioActual = 5000;
        } else {
            costoEnvioActual = 10000;
        }
    }
    updateTotalsDisplay();
}

function calcularFechaDespacho() {
    let fecha = new Date();
    let diasHabiles = 0;
    while (diasHabiles < 7) {
        fecha.setDate(fecha.getDate() + 1);
        if (fecha.getDay() !== 0 && fecha.getDay() !== 6) diasHabiles++;
    }
    const el = $("#despacho_fecha_estimada");
    if(el) {
        el.textContent = fecha.toLocaleDateString('es-ES', {weekday:'long', day:'numeric', month:'long'});
        el.dataset.isoDate = fecha.toISOString().split('T')[0];
    }
}

async function cargarSucursalesRetiro() {
    const select = $("#retiro_sucursal");
    if(!select) return;
    try {
        const res = await fetch('http://localhost:5000/api/sucursales_con_coords');
        const data = await res.json();
        select.innerHTML = '<option value="">Selecciona una sucursal</option>';
        data.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id_sucursal;
            opt.textContent = s.nombre_sucursal;
            select.appendChild(opt);
        });
    } catch(e) { console.error(e); }
}

// --- 2. RENDERIZADO ---

function renderCart() {
    const container = $("#cart-container");
    const shippingContainer = $("#shipping-container");
    const totalsContainer = $("#totals-container");
    
    const cart = getCart();

    if (!cart.length) {
        container.innerHTML = `<div class="cart-empty-box"><p>Tu carrito está vacío</p><a href="./productos.html" class="btn-lg">Explorar productos</a></div>`;
        if(shippingContainer) shippingContainer.style.display = 'none';
        if(totalsContainer) totalsContainer.style.display = 'none';
        updateCartBadge();
        return;
    }

    if(shippingContainer) shippingContainer.style.display = 'block';
    if(totalsContainer) totalsContainer.style.display = 'block';

    container.innerHTML = cart.map((p) => {
        const qty = Number(p.qty) || 0;
        const sub = p.price * qty;
        return `
          <div class="cart-item">
            <img class="cart-img" src="${p.image}" alt="${p.name}" onerror="this.src='../Public/imagenes/placeholder.jpg'"/>
            <div class="cart-info">
              <h3>${p.name}</h3>
              <p style="font-size:0.85em;color:#555;">SKU: ${p.sku}<br/>Talla: ${p.variation?.talla || 'Única'}</p>
              <p class="price">${formatCLP(p.price)}</p>
              <div class="cart-actions">
                <button class="qty-btn" data-action="dec" data-sku="${p.sku}">-</button>
                <span class="qty-val">${qty}</span>
                <button class="qty-btn" data-action="inc" data-sku="${p.sku}">+</button>
                <button class="remove-btn" data-sku="${p.sku}">Eliminar</button>
              </div>
            </div>
            <p class="cart-subtotal">${formatCLP(sub)}</p>
          </div>
        `;
    }).join("");

    updateTotalsDisplay();
    updateCartBadge();
}

// --- CORRECCIÓN CRÍTICA: ELIMINADA LA LECTURA DE DESCUENTO AQUÍ ---
function updateTotalsDisplay() {
    const subtotal = totalPrice();
    const iva = calculateIVA(subtotal);
    // Calculamos solo el total base (Producto + IVA + Envío)
    const totalBase = subtotal + iva + costoEnvioActual;

    // Actualizar textos base
    if($("#summary-subtotal")) $("#summary-subtotal").textContent = formatCLP(subtotal);
    if($("#summary-iva")) $("#summary-iva").textContent = formatCLP(iva);
    if($("#summary-envio")) $("#summary-envio").textContent = formatCLP(costoEnvioActual);
    
    // Mostramos temporalmente el total base. 
    // Si hay cupón, el evento de abajo hará que carrito.html lo sobrescriba en milisegundos.
    if($("#summary-total")) $("#summary-total").textContent = formatCLP(totalBase);
    if($("#totals-container")) $("#totals-container").dataset.total = totalBase;
    
    const container = $("#cart-container");
    if(container) container.dataset.total = String(Math.round(totalBase));

    // --- NOTIFICAR A CARRITO.HTML PARA QUE RECALCULE EL CUPÓN ---
    // Esto soluciona el problema del $0 y el cálculo en vivo
    window.dispatchEvent(new CustomEvent('cartBaseTotalUpdated'));
}


// --- 3. MANEJO DE PAGOS (VALIDACIÓN Y ENVÍO) ---

export function validarDatosEnvio() {
    const radioChecked = document.querySelector('input[name="tipo_entrega"]:checked');
    
    if (!radioChecked) {
        alert("⚠️ Por favor, selecciona una opción de entrega (Retiro o Despacho) antes de pagar.");
        document.getElementById('shipping-container')?.scrollIntoView({ behavior: 'smooth' });
        return null;
    }

    const tipo = radioChecked.value;
    let datos = {
        tipo_entrega: tipo,
        costo_envio: costoEnvioActual,
        datos_contacto: {},
        sucursal_id: null,
        fecha_entrega: null,
        bloque_horario: null
    };

    if (tipo === 'retiro') {
        const suc = $("#retiro_sucursal").value;
        const fecha = $("#retiro_fecha").value;
        const nombre = $("#retiro_nombre").value;
        const rut = $("#retiro_rut").value;
        
        if (!suc || !fecha || !nombre || !rut) {
            alert("⚠️ Por favor, completa todos los datos de retiro.");
            return null;
        }
        
        datos.sucursal_id = suc;
        datos.fecha_entrega = fecha;
        datos.bloque_horario = "Retiro Estándar";
        datos.datos_contacto = {
            nombre, rut,
            email: $("#retiro_email").value,
            telefono: $("#retiro_celular").value,
            tipo: 'Retiro en Tienda'
        };
        
    } else {
        const region = $("#select-region").value;
        const comuna = $("#input-comuna").value;
        const dir = $("#despacho_direccion").value;
        const nombre = $("#despacho_nombre").value;
        
        if (!region || !comuna || !dir || !nombre) {
            alert("⚠️ Por favor, completa todos los datos de despacho.");
            return null;
        }

        const sucursalActiva = getActiveBranchId(); 
        datos.sucursal_id = sucursalActiva ? sucursalActiva : 1;
        
        datos.fecha_entrega = $("#despacho_fecha_estimada").dataset.isoDate;
        datos.bloque_horario = $("#despacho_bloque").value;
        datos.datos_contacto = {
            nombre,
            region,
            ciudad: comuna,
            comuna,
            direccion: dir,
            email: $("#despacho_email").value,
            telefono: $("#despacho_celular").value,
            tipo: 'Despacho a Domicilio'
        };
    }
    return datos;
}

async function handleWebpayCheckout(btn) {
    const envioData = validarDatosEnvio();
    if (!envioData) return;

    const totalFinal = Number($("#totals-container").dataset.total);
    btn.setAttribute("disabled", "disabled");
    const oldText = btn.textContent;
    btn.textContent = "Procesando...";

    try {
        const cartItems = getCart();
        const subtotal = totalPrice();
        
        const pedidoPayload = {
            items: cartItems,
            total: totalFinal,
            subtotal: subtotal,
            iva: calculateIVA(subtotal),
            ...envioData 
        };

        localStorage.setItem('ultimaCompra', JSON.stringify({
            id: "PENDIENTE-" + Date.now(),
            fecha: new Date().toLocaleString(),
            ...pedidoPayload,
            items: cartItems 
        }));

        const resp = await postJSON("http://localhost:5000/api/crear-pedido", pedidoPayload);
        const idPedido = resp.id_pedido;

        const dataWP = await postJSON("http://localhost:3010/webpay/create", {
            amount: totalFinal,
            buyOrder: idPedido,
            sessionId: "USR-" + Date.now()
        });

        window.location.href = `${dataWP.url}?token_ws=${dataWP.token}`;

    } catch (e) {
        console.error(e);
        alert("Error al procesar Webpay: " + e.message);
        btn.removeAttribute("disabled");
        btn.textContent = oldText;
    }
}

async function handleMercadoPagoCheckout(btn) {
    const envioData = validarDatosEnvio();
    if (!envioData) return;

    const totalFinal = Number($("#totals-container").dataset.total);
    btn.setAttribute("disabled", "disabled");
    const oldText = btn.textContent;
    btn.textContent = "Procesando...";

    try {
        const cartItems = getCart();
        const subtotal = totalPrice();
        
        const pedidoPayload = {
            items: cartItems,
            total: totalFinal,
            subtotal: subtotal,
            iva: calculateIVA(subtotal),
            ...envioData
        };

        localStorage.setItem('ultimaCompra', JSON.stringify({
            id: "PENDIENTE-MP-" + Date.now(),
            fecha: new Date().toLocaleString(),
            ...pedidoPayload,
            items: cartItems
        }));

        const resp = await postJSON("http://localhost:5000/api/crear-pedido", pedidoPayload);
        const idPedido = resp.id_pedido;

        const itemsMP = cartItems.map(p => ({
            id: p.sku, 
            title: `${p.name} (Talla: ${p.variation?.talla || 'Única'})`, 
            unit_price: Math.round(p.price), 
            quantity: Number(p.qty), 
            currency_id: "CLP", 
            picture_url: p.image || undefined
        }));
        
        if(envioData.costo_envio > 0) {
            itemsMP.push({
                id: "ENVIO", 
                title: "Costo de Envío", 
                unit_price: envioData.costo_envio, 
                quantity: 1, 
                currency_id: "CLP"
            });
        }

        const respMP = await postJSON("http://localhost:3000/api/mercadopago/create", {
            items: itemsMP,
            external_reference: idPedido
        });

        const link = respMP.init_point || respMP.sandbox_init_point;
        window.location.href = link;

    } catch (e) {
        console.error(e);
        alert("Error al procesar MercadoPago: " + e.message);
        btn.removeAttribute("disabled");
        btn.textContent = oldText;
    }
}


// --- LISTENERS GENERALES ---
const container = $("#cart-container");
if(container) {
    container.addEventListener("click", (e) => {
        const t = e.target;
        if(t.classList.contains("qty-btn")) {
            const sku = t.dataset.sku;
            const item = getCart().find(i => i.sku === sku);
            if(!item) return;

            let qty = parseInt(item.qty);
            if (isNaN(qty) || qty < 1) qty = 1;

            const maxStock = parseInt(item.stock, 10);
            const limit = (!isNaN(maxStock) && maxStock > 0) ? maxStock : 10;

            if(t.dataset.action === 'inc') {
                if (qty < limit) {
                    qty++;
                } else {
                    alert(`Has alcanzado el límite de stock (${limit} unidades) para este producto.`);
                }
            } else {
                qty--; 
            }
            
            if(qty < 1) qty = 1;
            
            setQty(sku, qty);
            renderCart(); 
        }
        
        if(t.classList.contains("remove-btn")) {
            removeItem(t.dataset.sku);
            renderCart();
        }
    });
}

// Listeners de Botones de Acción Globales
$("#btn-clear")?.addEventListener("click", () => { saveCart([]); renderCart(); });

// Escuchar cambios en localStorage
window.addEventListener("storage", renderCart);