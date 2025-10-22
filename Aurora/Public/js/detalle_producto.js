// ../Public/js/detalle_producto.js

// Importamos addItem, formatCLP de cart.js
import { addItem, formatCLP } from "./cart.js";
// --- ▼▼▼ IMPORTACIÓN PARA GEOLOCALIZACIÓN ▼▼▼ ---
import { getNearestBranchId } from "./geolocation.js"; // Asegúrate que la ruta sea correcta
// --- ▲▲▲ FIN IMPORTACIÓN ▲▲▲ ---

const API_BASE = "http://localhost:5000";
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Estado global (sin cambios)
const state = {
  product: null,
  selectedVariation: null,
  availableStock: 0 // Se llenará con stock total o de sucursal
};

let stockErrorTimeout; // Timer (sin cambios)

// Función de traducción de color (sin cambios)
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

// DOMContentLoaded (sin cambios)
document.addEventListener("DOMContentLoaded", () => {
  loadProductDetails(); // Carga producto (ahora incluye lógica de sucursal)
  setupQuantityListeners();
  setupAddToCartListener();

  // Escuchar eventos de geolocalización
  window.addEventListener('branchLocated', handleBranchUpdate);
  window.addEventListener('branchLocationCleared', handleBranchUpdate);
});

/**
 * --- LOADPRODUCTDETAILS MODIFICADO ---
 * Obtiene el ID de sucursal cercana y lo añade a la URL de la API.
 */
async function loadProductDetails() {
  const hash = window.location.hash;
  const idProducto = hash.replace("#id=", "");

  if (!idProducto) {
    showError("No se especificó ningún producto."); return;
  }

  // --- OBTENER ID DE SUCURSAL Y CONSTRUIR URL ---
  const nearestBranchId = getNearestBranchId(); // Obtiene el ID desde geolocation.js
  let apiUrl = `${API_BASE}/api/producto/${idProducto}`; // URL base

  if (nearestBranchId) {
    apiUrl += `?sucursal_id=${nearestBranchId}`; // Añade el parámetro si existe
    console.log(`[Detalle Debug] Usando sucursal ID ${nearestBranchId} para buscar stock.`);
  } else {
    console.log("[Detalle Debug] No hay sucursal cercana guardada. Se mostrará stock total.");
  }
  // --- FIN CONSTRUCCIÓN URL ---

  try {
    // --- Usa la nueva apiUrl ---
    const res = await fetch(apiUrl);
    if (!res.ok) {
      if (res.status === 404) throw new Error("Producto no encontrado.");
      let errorBody = "Error desconocido del servidor.";
      try { errorBody = await res.text(); } catch(_) {}
      throw new Error(`Error ${res.status}: ${errorBody}`);
    }
    const data = await res.json();
    state.product = data;
    state.availableStock = data.stock_disponible !== undefined ? data.stock_disponible : 0;
    renderProduct(data); // Renderiza con el stock correcto
    showContent(); // Llama a la función para mostrar el contenido
  } catch (err) {
    console.error("Error al cargar producto:", err);
    showError(err.message);
  }
}

/**
 * --- RENDERPRODUCT (CON DEBUG LOG) ---
 * Muestra los datos, incluyendo el stock.
 */
function renderProduct(data) {
    // --- ▼▼▼ DEBUG LOG AÑADIDO ▼▼▼ ---
    console.log("[Render Debug] renderProduct llamada con data:", data);
    // --- ▲▲▲ FIN DEBUG LOG ▲▲▲ ---

    // Añade una comprobación básica de los datos recibidos
    if (!data || !data.producto || !data.imagenes || !data.variaciones) {
        console.error("[Render Debug] ¡Datos recibidos incompletos o inválidos!", data);
        showError("Error al procesar los datos del producto."); // Muestra un error al usuario
        return; // Detiene la ejecución si faltan datos clave
    }

    const { producto, imagenes, variaciones } = data;
    document.title = `Aurora | ${producto.nombre_producto}`;
    const nameEl = $("#product-name");       if(nameEl) nameEl.textContent = producto.nombre_producto;
    const skuEl = $("#product-sku");         if(skuEl) skuEl.textContent = producto.sku;
    const priceEl = $("#product-price");     if(priceEl) priceEl.textContent = formatCLP(producto.precio_producto);
    const descEl = $("#product-description"); if(descEl) descEl.textContent = producto.descripcion_producto || "No hay descripción disponible.";

    const mainImageContainer = $("#product-image-main");
    const thumbnailsContainer = $("#product-thumbnails");
    if(mainImageContainer) mainImageContainer.innerHTML = `<img src="${imagenes[0] || '../Public/imagenes/placeholder.jpg'}" alt="${producto.nombre_producto}">`;
    if(thumbnailsContainer) thumbnailsContainer.innerHTML = imagenes.map((img, index) => `<img src="${img}" alt="Miniatura ${index + 1}" class="${index === 0 ? 'active' : ''}" data-index="${index}">`).join("");
    setupImageGalleryListeners();

    const baseVariation = variaciones.find(v => v.talla === null);
    const sizedVariations = variaciones.filter(v => v.talla !== null);
    const tallasContainer = $("#product-tallas");
    if (tallasContainer){
        if (sizedVariations.length > 0) {
            tallasContainer.innerHTML = sizedVariations.map(v => `<button class="btn-talla" data-sku-variacion="${v.sku_variacion || ''}" data-talla="${v.talla}" data-color="${v.color || (baseVariation ? baseVariation.color : '')}">${v.talla}</button>`).join("");
            setupVariationListeners();
            state.selectedVariation = null;
        } else {
            tallasContainer.innerHTML = `<p>Talla Única</p>`;
            state.selectedVariation = baseVariation ? { sku_variacion: baseVariation.sku_variacion || producto.sku, talla: "Única", color: baseVariation.color || '' } : { sku_variacion: producto.sku, talla: "Única", color: '' };
        }
    } else { console.warn("Contenedor de tallas no encontrado."); }

    const colorToShow = baseVariation?.color || state.selectedVariation?.color || '';
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

    updateStockDisplay(); // Llama a función separada para actualizar UI de stock
}

/**
 * --- NUEVA FUNCIÓN ---
 * Actualiza la UI relacionada con el stock (texto y botones).
 */
function updateStockDisplay() {
    const stockContainer = $("#product-stock-container");
    const stockDisplay = $("#product-stock-display");
    const stock = state.availableStock;
    const btnPlus = $("#btn-quantity-plus");
    const btnMinus = $("#btn-quantity-minus");
    const inputQty = $("#product-quantity-input");
    const btnAdd = $("#btn-add-to-cart-detail");

    if (stockContainer && stockDisplay && btnPlus && btnMinus && inputQty && btnAdd) {
        if (stock > 0) {
            stockDisplay.textContent = `${stock} unidades disponibles`;
            stockContainer.classList.remove("out-of-stock");
            btnPlus.disabled = false; btnMinus.disabled = false; inputQty.disabled = false;
            btnAdd.disabled = !state.selectedVariation; // Habilita solo si hay talla seleccionada
            btnAdd.textContent = "Añadir al carrito";
        } else {
            stockDisplay.textContent = "AGOTADO"; stockContainer.classList.add("out-of-stock");
            btnPlus.disabled = true; btnMinus.disabled = true; inputQty.disabled = true;
            btnAdd.disabled = true; btnAdd.textContent = "Sin stock";
        }
        stockContainer.style.display = "block";
        if (parseInt(inputQty.value) > stock && stock > 0) {
            inputQty.value = stock;
        } else if (stock === 0) {
            inputQty.value = 1;
        }
    } else { console.warn("Faltan elementos HTML para mostrar el stock o los botones."); }
}

// setupImageGalleryListeners (sin cambios)
function setupImageGalleryListeners() {
  const thumbnails = $all(".product-gallery-thumbnails img");
  thumbnails.forEach(thumb => {
    thumb.addEventListener("click", () => {
      const mainImg = $("#product-image-main img");
      if(mainImg) mainImg.src = thumb.src;
      thumbnails.forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
    });
  });
}

// setupVariationListeners (sin cambios)
function setupVariationListeners() {
  const variationButtons = $all(".btn-talla");
  variationButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      state.selectedVariation = {
          sku_variacion: btn.dataset.skuVariacion,
          talla: btn.dataset.talla,
          color: btn.dataset.color || ''
      };
      variationButtons.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      const variationErrorEl = $("#variation-error");
      if(variationErrorEl) variationErrorEl.style.display = "none";
      const btnAdd = $("#btn-add-to-cart-detail"); // Habilita AddToCart al seleccionar talla
      if(btnAdd && state.availableStock > 0) { btnAdd.disabled = false; }
      const colorContainer = $("#product-color-container"); // Actualiza color
      if (btn.dataset.color && colorContainer) {
         const nombreColor = btn.dataset.color; const colorCSS = traducirColorACSS(nombreColor);
         const colorNameEl = $("#product-color-name"); const colorSwatchEl = $("#product-color-swatch");
         if(colorNameEl) colorNameEl.textContent = nombreColor;
         if(colorSwatchEl) {
             colorSwatchEl.style.backgroundColor = colorCSS;
             if (colorCSS.toLowerCase() === "white" || colorCSS.toLowerCase() === "beige" || colorCSS.toLowerCase() === "#ffffff") { colorSwatchEl.style.borderColor = "#999"; } else { colorSwatchEl.style.borderColor = "#ccc"; }
         }
         colorContainer.style.display = "block";
      }
    });
  });
}

// setupQuantityListeners (sin cambios)
function setupQuantityListeners() {
  const btnMinus = $("#btn-quantity-minus"); const btnPlus = $("#btn-quantity-plus");
  const input = $("#product-quantity-input");
  if(!btnMinus || !btnPlus || !input) { console.warn("Elementos selector cantidad no encontrados."); return; }
  btnPlus.addEventListener("click", () => {
    const stock = state.availableStock; hideStockError();
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

// setupAddToCartListener (sin cambios)
function setupAddToCartListener() {
  const btnAdd = $("#btn-add-to-cart-detail");
  if(!btnAdd){ console.warn("Botón 'Añadir al carrito' no encontrado."); return; }
  btnAdd.addEventListener("click", () => {
    hideStockError();
    if (!state.selectedVariation) { const ve=$("#variation-error"); if(ve) ve.style.display="block"; return; }
    const quantityInput = $("#product-quantity-input");
    if(!quantityInput) { console.error("Input cantidad no encontrado."); return;}
    const quantity = parseInt(quantityInput.value, 10);
    if (isNaN(quantity) || quantity < 1) { alert("Cantidad inválida."); quantityInput.value = 1; return; }
    if (quantity > state.availableStock) { showStockError(state.availableStock); return; }
    const { producto } = state.product; const { sku_variacion, talla, color } = state.selectedVariation;
    const itemToAdd = {
      id: producto.id_producto, name: producto.nombre_producto, price: producto.precio_producto,
      image: state.product.imagenes[0] || '../Public/imagenes/placeholder.jpg',
      sku: sku_variacion || producto.sku, variation: { talla: talla, color: color || '' }
    };
    addItem(itemToAdd, quantity); // Llama a addItem (que abrirá el modal)
    const btn = btnAdd; const prevText = btn.textContent;
    btn.textContent = "¡Añadido!"; btn.disabled = true;
    setTimeout(() => {
      if(state.availableStock > 0){ btn.textContent = prevText; btn.disabled = false; }
      else { btn.textContent = "Sin stock"; }
      if(quantityInput) quantityInput.value = 1;
    }, 1000);
  });
}

// Funciones de Ayuda (Stock Error) (sin cambios)
function showStockError(stock) { const em=$("#stock-error"); const eq=$("#stock-error-qty"); if(em&&eq){ eq.textContent=stock; em.style.display="block"; clearTimeout(stockErrorTimeout); stockErrorTimeout=setTimeout(()=>{if(em) em.style.display="none";},3000);} else {console.warn("Elementos error stock no encontrados.");}}
function hideStockError() { clearTimeout(stockErrorTimeout); const em=$("#stock-error"); if(em) em.style.display="none"; }

/**
 * --- showContent CON DEBUG LOGS ---
 * Muestra el contenedor principal del producto.
 */
function showContent() {
  console.log("[ShowContent Debug] showContent llamada."); // DEBUG
  const loading = $("#product-loading");
  const errorEl = $("#product-error");
  const dataContainer = $("#product-data"); // El contenedor principal que estaba oculto

  console.log("[ShowContent Debug] Contenedor #product-data encontrado:", dataContainer); // DEBUG

  if(loading) loading.style.display = "none";
  if(errorEl) errorEl.style.display = "none";

  // Comprueba si encontró el contenedor antes de cambiar el estilo
  if(dataContainer) {
    dataContainer.style.display = "grid"; // Cambia a 'grid' (o 'block' si prefieres)
    console.log("[ShowContent Debug] Estilo de #product-data cambiado a 'grid'. ¿Se ve el producto?"); // DEBUG
  } else {
    console.error("[ShowContent Debug] ¡ERROR! No se encontró el contenedor #product-data para mostrar.");
    // Podrías llamar a showError aquí si quieres que el usuario vea un error
    // showError("Error al mostrar la información del producto.");
  }
}


// showError (sin cambios)
function showError(message) {
  const loading = $("#product-loading"); const data = $("#product-data");
  const errorEl = $("#product-error"); const errorMsgEl = $("#product-error-message");
  if(loading) loading.style.display = "none"; if(data) data.style.display = "none";
  if(errorMsgEl) errorMsgEl.textContent = message; if(errorEl) errorEl.style.display = "block";
}


/**
 * --- NUEVO: Manejador para eventos de geolocalización ---
 * Vuelve a cargar los detalles si la sucursal cambia o se limpia después de la carga inicial.
 */
function handleBranchUpdate() {
    console.log("[Detalle Debug] Actualización de sucursal detectada. Recargando detalles...");
    // Vuelve a llamar a loadProductDetails para obtener el stock actualizado para la nueva/ninguna sucursal
    loadProductDetails();
}