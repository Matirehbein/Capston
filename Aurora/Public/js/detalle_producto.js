// ../Public/js/detalle_producto.js

// Importamos addItem, formatCLP de cart.js
import { addItem, formatCLP } from "./cart.js";
// Importamos getActiveBranchId de geolocation.js
import { getActiveBranchId } from "./geolocation.js";

const API_BASE = "http://localhost:5000";
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Estado global para la página
const state = {
  product: null,
  selectedVariation: null,
  availableStock: 0, // Stock de la talla SELECCIONADA
  totalStock: 0 // Stock TOTAL del producto (suma de tallas)
};

let stockErrorTimeout; // Timer para el mensaje de error de stock

// Función para traducir nombres de color a CSS
function traducirColorACSS(nombreColor) {
  const mapaColores = {
    "rojo": "red", "azul": "blue", "verde": "green", "negro": "black",
    "blanco": "white", "gris": "gray", "amarillo": "yellow", "naranja": "orange",
    "naranjo": "orange", "morado": "purple", "rosado": "pink", "azul marino": "navy",
    "burdeo": "maroon", "beige": "beige", "cafe": "saddlebrown", "café": "saddlebrown",
    "celeste": "lightblue"
  };
  if (!nombreColor) return "lightgray";
  const colorNormalizado = String(nombreColor).toLowerCase().trim();
  return mapaColores[colorNormalizado] || colorNormalizado || "lightgray";
}

// Se ejecuta cuando el HTML está listo
document.addEventListener("DOMContentLoaded", () => {
  loadProductDetails(); // Carga producto (ahora incluye lógica de sucursal)
  setupQuantityListeners(); // Configura botones +/-
  setupAddToCartListener(); // Configura botón "Añadir al carrito"

  // Escuchar eventos de geolocalización
  window.addEventListener('branchLocated', handleBranchUpdate);
  window.addEventListener('branchLocationCleared', handleBranchUpdate);
});

/**
 * Carga los detalles del producto (incluyendo stock por sucursal)
 */
async function loadProductDetails() {
  const hash = window.location.hash;
  const idProducto = hash.replace("#id=", "");
  if (!idProducto) { showError("No se especificó ningún producto."); return; }
  
  const nearestBranchId = getActiveBranchId();
  let apiUrl = `${API_BASE}/api/producto/${idProducto}`;
  if (nearestBranchId) { apiUrl += `?sucursal_id=${nearestBranchId}`; }
  console.log(`[Detalle Debug] Llamando a API: ${apiUrl}`);

  try {
    const res = await fetch(apiUrl);
    if (!res.ok) { throw new Error(`Error ${res.status}`); }
    const data = await res.json();
    
    state.product = data;
    // 'stock_disponible' de la API es el TOTAL (suma de tallas)
    state.totalStock = data.stock_disponible !== undefined ? data.stock_disponible : 0;
    state.availableStock = 0; // Se define al seleccionar talla
    
    renderProduct(data);
    showContent();
  } catch (err) { console.error("Error al cargar producto:", err); showError(err.message); }
}

/**
 * --- RENDERPRODUCT (COMPLETO) ---
 * Muestra el stock TOTAL al inicio.
 * Crea un botón "Estándar" para productos de talla única.
 * Marca tallas agotadas.
 * Llama a la función de Zoom.
 */
function renderProduct(data) {
    console.log("[Render Debug] renderProduct llamada con data:", data);
    if (!data || !data.producto || !data.imagenes || !data.variaciones) {
        console.error("[Render Debug] Datos recibidos incompletos!", data);
        showError("Error al procesar datos."); return;
    }

    const { producto, imagenes, variaciones } = data;
    document.title = `Aurora | ${producto.nombre_producto || 'Producto'}`;
    
    // --- Rellenar Info Básica y Precios ---
    const nameEl = $("#product-name");       if(nameEl) nameEl.textContent = producto.nombre_producto;
    const skuEl = $("#product-sku");         if(skuEl) skuEl.textContent = producto.sku;
    const descEl = $("#product-description"); if(descEl) descEl.textContent = producto.descripcion_producto || "No hay descripción disponible.";
    
    const priceContainer = $("#product-price");
    if (priceContainer) {
        const precioOriginal = producto.precio_producto || 0;
        const precioOferta = producto.precio_oferta;
        const descuentoPct = producto.descuento_pct;
        let displayPriceHtml;
        if (precioOferta !== null && precioOferta < precioOriginal) {
            displayPriceHtml = `
              <span class="producto-precio-original" style="font-size: 0.7em; text-decoration: line-through; color: #888; margin-right: 0.5em;">${formatCLP(precioOriginal)}</span>
              <span class="producto-precio-oferta" style="color: var(--color-oferta, red); font-weight: bold;">${formatCLP(precioOferta)}</span>
              ${descuentoPct ? `<span class="descuento-tag" style="background-color: var(--color-oferta, red); color: white; font-size: 0.7em; padding: 2px 5px; border-radius: 3px; margin-left: 0.5em; vertical-align: middle;">-${Math.round(descuentoPct)}%</span>` : ''}
            `;
            priceContainer.style.fontSize = "2rem";
        } else {
            displayPriceHtml = `<span>${formatCLP(precioOriginal)}</span>`;
            priceContainer.style.fontSize = "2rem";
            priceContainer.style.color = "var(--color-primary, #000)";
        }
        priceContainer.innerHTML = displayPriceHtml;
    } else { console.warn("Elemento #product-price no encontrado."); }

    // --- Rellenar Galería (con ID para Zoom) ---
    const mainImageContainer = $("#product-image-main");
    const thumbnailsContainer = $("#product-thumbnails");
    if(mainImageContainer) {
        mainImageContainer.innerHTML = `<img id="main-product-image" src="${imagenes[0] || '../Public/imagenes/placeholder.jpg'}" alt="${producto.nombre_producto}">`;
    }
    if(thumbnailsContainer) thumbnailsContainer.innerHTML = imagenes.map((img, index) => `<img src="${img}" alt="Miniatura ${index + 1}" class="${index === 0 ? 'active' : ''}" data-index="${index}">`).join("");
    
    setupImageGalleryListeners(); // Configura clics en miniaturas
    setupImageZoom(); // --- LLAMA A LA FUNCIÓN DE ZOOM ---
    
    // --- Lógica Talla/Color (con botón "Estándar") ---
    const baseVariation = variaciones.find(v => v.talla === null);
    const sizedVariations = variaciones.filter(v => v.talla !== null);
    const tallasContainer = $("#product-tallas");
    
    if (tallasContainer){
        if (sizedVariations.length > 0) { // Caso 1: Tallas S, M, L...
            tallasContainer.innerHTML = sizedVariations.map(v => {
                const stockDeTalla = parseInt(v.stock, 10) || 0; 
                const isDisabled = stockDeTalla <= 0;
                return `
                    <button class="btn-talla ${isDisabled ? 'disabled-talla' : ''}" 
                            data-sku-variacion="${v.sku_variacion || producto.sku}" 
                            data-talla="${v.talla}" 
                            data-color="${v.color || (baseVariation ? baseVariation.color : '')}"
                            data-stock="${stockDeTalla}"
                            ${isDisabled ? 'disabled' : ''}>
                        ${v.talla}
                    </button>
                `;
            }).join("");
            state.selectedVariation = null; // Nada seleccionado al inicio
        
        } else if (baseVariation) { // Caso 2: Solo Talla Única (ej. Mochila)
            const stockUnica = parseInt(baseVariation.stock, 10) || 0;
            const isDisabled = stockUnica <= 0;
            tallasContainer.innerHTML = `
                <button class="btn-talla ${isDisabled ? 'disabled-talla' : ''}"
                        data-sku-variacion="${baseVariation.sku_variacion || producto.sku}"
                        data-talla="Estándar" 
                        data-color="${baseVariation.color || ''}"
                        data-stock="${stockUnica}"
                        ${isDisabled ? 'disabled' : ''}>
                    Estándar
                </button>
            `;
            state.selectedVariation = null; // Requiere clic
        
        } else { // Caso 3: Sin variaciones (raro)
            tallasContainer.innerHTML = `<p>Tallas no disponibles</p>`;
            state.selectedVariation = null;
        }
        
        setupVariationListeners(); // Llama a los listeners para los botones creados
        
    } else { console.warn("Contenedor de tallas no encontrado."); }

    // --- Renderizar Color (basado en la variación base) ---
    const colorToShow = baseVariation?.color || '';
    const colorContainer = $("#product-color-container");
    const colorNameEl = $("#product-color-name");
    const colorSwatchEl = $("#product-color-swatch");
    if (colorToShow && colorContainer && colorNameEl && colorSwatchEl) {
        const colorCSS = traducirColorACSS(colorToShow);
        colorNameEl.textContent = colorToShow;
        colorSwatchEl.style.backgroundColor = colorCSS;
        if (colorCSS.toLowerCase() === "white" || colorCSS.toLowerCase() === "beige" || colorCSS.toLowerCase() === "#ffffff") { colorSwatchEl.style.borderColor = "#999"; } else { colorSwatchEl.style.borderColor = "#ccc"; }
        colorContainer.style.display = "block";
    } else if (colorContainer) { colorContainer.style.display = "none"; }

    // --- Renderizar Stock (muestra total al inicio) ---
    updateStockDisplay(true); // true = Carga inicial
}

/**
 * Actualiza la UI del Stock (muestra total o por talla)
 */
function updateStockDisplay(isInitialLoad = false) {
    const stockContainer = $("#product-stock-container");
    const stockDisplay = $("#product-stock-display");
    const stockSeleccionado = state.availableStock;
    const stockTotal = state.totalStock;
    const btnPlus = $("#btn-quantity-plus");
    const btnMinus = $("#btn-quantity-minus");
    const inputQty = $("#product-quantity-input");
    const btnAdd = $("#btn-add-to-cart-detail");

    if (!stockContainer || !stockDisplay || !btnPlus || !btnMinus || !inputQty || !btnAdd) {
        console.warn("Faltan elementos HTML para mostrar el stock.");
        return;
    }

    stockContainer.style.display = "block";
    stockContainer.classList.remove("out-of-stock");

    if (isInitialLoad || !state.selectedVariation) {
        // --- ESTADO INICIAL (NADA SELECCIONADO) ---
        stockDisplay.textContent = `${stockTotal} unidades disponibles`; // Muestra TOTAL
        btnPlus.disabled = true; btnMinus.disabled = true; inputQty.disabled = true;
        btnAdd.disabled = true; btnAdd.textContent = "Selecciona una talla";
        
    } else {
        // --- TALLA SELECCIONADA ---
        stockDisplay.textContent = `${stockSeleccionado} unidades disponibles`; // Muestra stock de TALLA

        if (stockSeleccionado > 0) {
            btnPlus.disabled = false; btnMinus.disabled = false; inputQty.disabled = false;
            btnAdd.disabled = false; btnAdd.textContent = "Añadir al carrito";
        } else {
            stockDisplay.textContent = `0 unidades disponibles`;
            stockContainer.classList.add("out-of-stock");
            btnPlus.disabled = true; btnMinus.disabled = true; inputQty.disabled = true;
            btnAdd.disabled = true; btnAdd.textContent = "Agotado";
        }
    }
    
    inputQty.value = 1; 
    if (stockSeleccionado > 0 && parseInt(inputQty.value) > stockSeleccionado) {
        inputQty.value = stockSeleccionado;
    }
}

/**
 * Añade listeners a las miniaturas (resetea el zoom)
 */
function setupImageGalleryListeners() {
  const thumbnails = $all(".product-gallery-thumbnails img");
  const mainImage = $("#main-product-image"); 
  if (!mainImage) { return; }

  thumbnails.forEach(thumb => {
    thumb.addEventListener("click", () => {
      // Resetea el zoom al cambiar de imagen
      mainImage.style.transform = "scale(1)";
      mainImage.style.transformOrigin = "center center";

      mainImage.src = thumb.src;
      thumbnails.forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
    });
  });
}

/**
 * Añade listeners a los botones de talla (habilitados)
 */
function setupVariationListeners() {
  const variationButtons = $all(".product-variations-options .btn-talla:not([disabled])");
  
  variationButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const stockDeTalla = parseInt(btn.dataset.stock, 10) || 0;
      console.log(`Talla ${btn.dataset.talla} seleccionada, stock: ${stockDeTalla}`);

      state.selectedVariation = {
          sku_variacion: btn.dataset.skuVariacion,
          talla: btn.dataset.talla,
          color: btn.dataset.color || '',
          stock: stockDeTalla
      };
      state.availableStock = stockDeTalla;

      $all(".product-variations-options .btn-talla").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      
      const variationErrorEl = $("#variation-error");
      if(variationErrorEl) variationErrorEl.style.display = "none";

      updateStockDisplay(false); // Actualiza UI de stock (no es carga inicial)

      const colorContainer = $("#product-color-container");
      if (btn.dataset.color && colorContainer) { /* ... tu lógica de color ... */ }
    });
  });
}

/**
 * Añade listeners al selector de cantidad
 */
function setupQuantityListeners() {
  const btnMinus = $("#btn-quantity-minus"); const btnPlus = $("#btn-quantity-plus");
  const input = $("#product-quantity-input");
  if(!btnMinus || !btnPlus || !input) { console.warn("Elementos selector cantidad no encontrados."); return; }
  
  btnPlus.addEventListener("click", () => {
    const stock = state.availableStock; // Stock de la talla seleccionada
    hideStockError();
    try { let cv = parseInt(input.value, 10); if (isNaN(cv)) cv = 1; if (cv < stock && cv < 99) { input.value = cv + 1; } else { showStockError(stock); } } catch (e) { input.value = 1; }
  });
  btnMinus.addEventListener("click", () => {
    hideStockError();
    try { let cv = parseInt(input.value, 10); if (isNaN(cv)) cv = 1; if (cv > 1) { input.value = cv - 1; } } catch (e) { input.value = 1; }
  });
  input.addEventListener("change", () => {
    const stock = state.availableStock; hideStockError();
    try { let cv = parseInt(input.value, 10); if (isNaN(cv) || cv < 1) { input.value = 1; } if (stock > 0 && cv > stock) { input.value = stock; showStockError(stock); } else if (stock === 0) { input.value = 1; } if (cv > 99) { input.value = 99; } } catch (e) { input.value = 1; }
  });
}

/**
 * Añade listener al botón "Añadir al carrito"
 */
function setupAddToCartListener() {
  const btnAdd = $("#btn-add-to-cart-detail");
  if(!btnAdd){ console.warn("Botón 'Añadir al carrito' no encontrado."); return; }
  
  btnAdd.addEventListener("click", () => {
    hideStockError();
    // 1. Validar talla
    if (!state.selectedVariation) { const ve=$("#variation-error"); if(ve) ve.style.display="block"; return; }
    
    // 2. Leer Cantidad
    const quantityInput = $("#product-quantity-input");
    if(!quantityInput) { console.error("Input cantidad no encontrado."); return;}
    const quantity = parseInt(quantityInput.value, 10);
    
    // 3. Validar cantidad
    if (isNaN(quantity) || quantity < 1) { alert("Cantidad inválida."); quantityInput.value = 1; return; }
    
    // 4. Validar Stock (contra la talla seleccionada)
    if (quantity > state.availableStock) { showStockError(state.availableStock); return; }
    
    // 5. Preparar item
    const { producto } = state.product;
    const { sku_variacion, talla, color } = state.selectedVariation;
    const priceForCart = producto.precio_oferta ?? producto.precio_producto;
    const itemToAdd = {
      id: producto.id_producto, name: producto.nombre_producto, price: priceForCart,
      image: state.product.imagenes[0] || '../Public/imagenes/placeholder.jpg',
      sku: sku_variacion || producto.sku,
      variation: { talla: talla, color: color || '' }
    };
    
    // 6. Añadir al carrito (y mostrar modal)
    addItem(itemToAdd, quantity);
    
    // 7. Feedback visual y reseteo
    const btn = btnAdd; const prevText = btn.textContent;
    btn.textContent = "¡Añadido!"; btn.disabled = true;
    setTimeout(() => {
      // Resetea todo al estado inicial (post-carga)
      btn.textContent = "Selecciona una talla"; // Texto original del estado inicial
      // btn.disabled = true; // Ya está deshabilitado por updateStockDisplay
      if(quantityInput) quantityInput.value = 1;
      state.selectedVariation = null; // Deselecciona la talla
      state.availableStock = 0; // Resetea stock seleccionado
      updateStockDisplay(true); // Vuelve a mostrar el stock TOTAL y deshabilita botones
      $all(".product-variations-options .btn-talla").forEach(b => b.classList.remove("selected")); // Quita selección visual
    }, 1000); // 1 segundo de feedback
  });
}

// --- Funciones de Ayuda (Stock Error) (sin cambios) ---
function showStockError(stock) { const em=$("#stock-error"); const eq=$("#stock-error-qty"); if(em&&eq){ eq.textContent=stock; em.style.display="block"; clearTimeout(stockErrorTimeout); stockErrorTimeout=setTimeout(()=>{if(em) em.style.display="none";},3000);} else {console.warn("Elementos error stock no encontrados.");}}
function hideStockError() { clearTimeout(stockErrorTimeout); const em=$("#stock-error"); if(em) em.style.display="none"; }

// --- Funciones de UI (showError, showContent) (sin cambios) ---
function showError(message) {
  const loading = $("#product-loading"); const data = $("#product-data");
  const errorEl = $("#product-error"); const errorMsgEl = $("#product-error-message");
  if(loading) loading.style.display = "none"; if(data) data.style.display = "none";
  if(errorMsgEl) errorMsgEl.textContent = message; if(errorEl) errorEl.style.display = "block";
}
function showContent() {
  console.log("[ShowContent Debug] showContent llamada.");
  const loading = $("#product-loading"); const errorEl = $("#product-error");
  const dataContainer = $("#product-data");
  console.log("[ShowContent Debug] Contenedor #product-data encontrado:", dataContainer);
  if(loading) loading.style.display = "none";
  if(errorEl) errorEl.style.display = "none";
  if(dataContainer) {
    dataContainer.style.display = "grid";
    console.log("[ShowContent Debug] Estilo de #product-data cambiado a 'grid'.");
  } else {
    console.error("[ShowContent Debug] ¡ERROR CRÍTICO! No se encontró #product-data.");
    showError("Error al intentar mostrar la información del producto.");
  }
}

// --- handleBranchUpdate (sin cambios) ---
function handleBranchUpdate() {
    console.log("[Detalle Debug] Actualización de sucursal detectada. Recargando detalles...");
    loadProductDetails();
}


/**
 * --- FUNCIÓN DE ZOOM (ESTILO LUPA) ---
 */
function setupImageZoom() {
  const container = $("#product-image-main");
  const img = $("#main-product-image"); 

  if (!container || !img) {
    console.warn("No se encontraron elementos (contenedor o imagen) para el zoom.");
    return;
  }
  
  const ZOOM_LEVEL = 2.0; // Define el nivel de zoom (ej: 2x)

  container.addEventListener("mouseenter", () => {
    img.style.transition = 'transform 0.1s ease-out'; // Transición suave al entrar
    img.style.transform = `scale(${ZOOM_LEVEL})`;
  });

  container.addEventListener("mousemove", (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const xPercent = (x / rect.width) * 100;
    const yPercent = (y / rect.height) * 100;
    img.style.transition = 'none'; // Movimiento instantáneo
    img.style.transformOrigin = `${xPercent}% ${yPercent}%`;
  });

  container.addEventListener("mouseleave", () => {
    img.style.transition = 'transform 0.2s ease-out'; // Transición suave al salir
    img.style.transform = "scale(1)";
    img.style.transformOrigin = "center center";
  });
}
// --- FIN FUNCIÓN ZOOM ---