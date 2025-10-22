// ../Public/js/detalle_producto.js

// Importamos addItem, formatCLP de cart.js
import { addItem, formatCLP } from "./cart.js";
// --- ▼▼▼ IMPORTACIÓN PARA GEOLOCALIZACIÓN ▼▼▼ ---
import { getNearestBranchId } from "./geolocation.js"; // Asegúrate que la ruta sea correcta
// --- ▲▲▲ FIN IMPORTACIÓN ▲▲▲ ---

const API_BASE = "http://localhost:5000";
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Estado global
const state = {
  product: null,
  selectedVariation: null,
  availableStock: 0 // Se llenará con stock total o de sucursal
};

let stockErrorTimeout; // Timer para ocultar el error de stock

// Función de traducción de color
function traducirColorACSS(nombreColor) {
  const mapaColores = {
    "rojo": "red", "azul": "blue", "verde": "green", "negro": "black",
    "blanco": "white", "gris": "gray", "amarillo": "yellow", "naranja": "orange",
    "naranjo": "orange", "morado": "purple", "rosado": "pink", "azul marino": "navy",
    "burdeo": "maroon", "beige": "beige", "cafe": "saddlebrown", "café": "saddlebrown",
    "celeste": "lightblue"
    // Puedes añadir más colores aquí si es necesario
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

  // Escuchar eventos de geolocalización por si cambian después de la carga inicial
  window.addEventListener('branchLocated', handleBranchUpdate);
  window.addEventListener('branchLocationCleared', handleBranchUpdate);
});

/**
 * Carga los detalles del producto desde la API.
 * Obtiene el ID de sucursal cercana y lo añade a la URL de la API.
 */
async function loadProductDetails() {
  const hash = window.location.hash; // Lee #id=X
  const idProducto = hash.replace("#id=", ""); // Extrae el ID

  if (!idProducto) {
    showError("No se especificó ningún producto."); return;
  }

  // Obtiene el ID de la sucursal guardado por geolocation.js
  const nearestBranchId = getNearestBranchId();
  let apiUrl = `${API_BASE}/api/producto/${idProducto}`; // URL base de la API

  // Añade el parámetro de sucursal si existe
  if (nearestBranchId) {
    apiUrl += `?sucursal_id=${nearestBranchId}`;
    console.log(`[Detalle Debug] Usando sucursal ID ${nearestBranchId} para buscar stock.`);
  } else {
    console.log("[Detalle Debug] No hay sucursal cercana guardada. Se mostrará stock total.");
  }

  try {
    // Llama a la API (con o sin filtro de sucursal)
    const res = await fetch(apiUrl);
    if (!res.ok) { // Manejo de errores de la respuesta
      if (res.status === 404) throw new Error("Producto no encontrado.");
      let errorBody = `Error ${res.status}`;
      try { errorBody += `: ${await res.text()}`; } catch(_) {} // Intenta obtener más detalles
      throw new Error(errorBody);
    }
    const data = await res.json(); // Convierte la respuesta a JSON

    // Guarda los datos recibidos en el estado global
    state.product = data;
    // Guarda el stock (ya viene calculado por el backend: total o por sucursal)
    state.availableStock = data.stock_disponible !== undefined ? data.stock_disponible : 0;

    renderProduct(data); // Llama a la función que pinta el HTML
    showContent(); // Llama a la función que hace visible el contenido
  } catch (err) {
    console.error("Error al cargar producto:", err);
    showError(err.message); // Muestra error en la UI
  }
}

/**
 * Pinta el HTML con los datos del producto recibidos.
 * Incluye lógica para mostrar precios de oferta.
 */
function renderProduct(data) {
    console.log("[Render Debug] renderProduct llamada con data:", data); // Log para depurar
    // Verificación básica de datos
    if (!data || !data.producto || !data.imagenes || !data.variaciones) {
        console.error("[Render Debug] ¡Datos recibidos incompletos o inválidos!", data);
        showError("Error al procesar los datos del producto."); return;
    }

    // 'producto' ahora SIEMPRE tiene las claves 'precio_oferta' y 'descuento_pct' (pueden ser null)
    const { producto, imagenes, variaciones } = data;

    // Rellenar información básica
    document.title = `Aurora | ${producto.nombre_producto || 'Producto'}`;
    const nameEl = $("#product-name");       if(nameEl) nameEl.textContent = producto.nombre_producto;
    const skuEl = $("#product-sku");         if(skuEl) skuEl.textContent = producto.sku;
    const descEl = $("#product-description"); if(descEl) descEl.textContent = producto.descripcion_producto || "No hay descripción disponible.";

    // --- LÓGICA DE PRECIO (INCLUYE OFERTA) ---
    const priceContainer = $("#product-price"); // El <p> donde va el precio
    if (priceContainer) {
        const precioOriginal = producto.precio_producto || 0;
        const precioOferta = producto.precio_oferta; // Viene del backend (puede ser null)
        const descuentoPct = producto.descuento_pct; // Viene del backend (puede ser null)
        let displayPriceHtml;

        // Comprueba si hay oferta válida y si es menor al precio original
        if (precioOferta !== null && precioOferta < precioOriginal) {
            // Mostrar ambos precios y tag de descuento
            displayPriceHtml = `
              <span class="producto-precio-original" style="font-size: 0.7em; text-decoration: line-through; color: #888; margin-right: 0.5em;">${formatCLP(precioOriginal)}</span>
              <span class="producto-precio-oferta" style="color: var(--color-oferta, red); font-weight: bold;">${formatCLP(precioOferta)}</span>
              ${descuentoPct ? `<span class="descuento-tag" style="background-color: var(--color-oferta, red); color: white; font-size: 0.7em; padding: 2px 5px; border-radius: 3px; margin-left: 0.5em; vertical-align: middle;">-${Math.round(descuentoPct)}%</span>` : ''}
            `;
            // Aplica estilos al contenedor si es necesario (ej. mantener tamaño)
            priceContainer.style.fontSize = "2rem";
        } else {
            // Mostrar solo precio normal si no hay oferta
            displayPriceHtml = `<span>${formatCLP(precioOriginal)}</span>`;
            priceContainer.style.fontSize = "2rem"; // Asegura tamaño normal
            priceContainer.style.color = "var(--color-primary, #000)"; // Asegura color normal
        }
        priceContainer.innerHTML = displayPriceHtml; // Reemplaza el contenido del <p>
    } else {
        console.warn("Elemento #product-price no encontrado.");
    }
    // --- FIN LÓGICA DE PRECIO ---

    // Rellenar Galería de Imágenes
    const mainImageContainer = $("#product-image-main");
    const thumbnailsContainer = $("#product-thumbnails");
    if(mainImageContainer) mainImageContainer.innerHTML = `<img src="${imagenes[0] || '../Public/imagenes/placeholder.jpg'}" alt="${producto.nombre_producto}">`;
    if(thumbnailsContainer) thumbnailsContainer.innerHTML = imagenes.map((img, index) => `<img src="${img}" alt="Miniatura ${index + 1}" class="${index === 0 ? 'active' : ''}" data-index="${index}">`).join("");
    setupImageGalleryListeners(); // Añade listeners a las miniaturas

    // Lógica para Tallas y Color Base
    const baseVariation = variaciones.find(v => v.talla === null);
    const sizedVariations = variaciones.filter(v => v.talla !== null);
    const tallasContainer = $("#product-tallas");
    if (tallasContainer){ // Verifica si existe el contenedor de tallas
        if (sizedVariations.length > 0) { // Si hay tallas específicas (S, M, L...)
            tallasContainer.innerHTML = sizedVariations.map(v =>
                `<button class="btn-talla"
                         data-sku-variacion="${v.sku_variacion || ''}"
                         data-talla="${v.talla}"
                         data-color="${v.color || (baseVariation ? baseVariation.color : '')}">
                    ${v.talla}
                 </button>`
            ).join("");
            setupVariationListeners(); // Añade listeners a los botones de talla
            state.selectedVariation = null; // Ninguna talla seleccionada al inicio
        } else { // Si no hay tallas específicas, es Talla Única
            tallasContainer.innerHTML = `<p>Talla Única</p>`;
            // Selecciona automáticamente la variación (usa la base si existe, si no un fallback)
            state.selectedVariation = baseVariation ? {
                sku_variacion: baseVariation.sku_variacion || producto.sku,
                talla: "Única",
                color: baseVariation.color || ''
            } : { // Fallback si no hay ni variación base (raro)
                sku_variacion: producto.sku,
                talla: "Única",
                color: ''
            };
        }
    } else { console.warn("Contenedor de tallas #product-tallas no encontrado."); }

    // Rellenar Color (basado en la variación base o la seleccionada)
    const colorToShow = baseVariation?.color || state.selectedVariation?.color || ''; // Intenta obtener color
    const colorContainer = $("#product-color-container");
    const colorNameEl = $("#product-color-name");
    const colorSwatchEl = $("#product-color-swatch");
    if (colorToShow && colorContainer && colorNameEl && colorSwatchEl) { // Si hay color y elementos existen
        const colorCSS = traducirColorACSS(colorToShow);
        colorNameEl.textContent = colorToShow;
        colorSwatchEl.style.backgroundColor = colorCSS;
        // Ajusta borde para colores claros
        if (colorCSS.toLowerCase() === "white" || colorCSS.toLowerCase() === "beige" || colorCSS.toLowerCase() === "#ffffff") {
           colorSwatchEl.style.borderColor = "#999";
        } else { colorSwatchEl.style.borderColor = "#ccc"; }
        colorContainer.style.display = "block"; // Muestra el contenedor de color
    } else if (colorContainer) {
        colorContainer.style.display = "none"; // Oculta si no hay color que mostrar
    }

    // Actualiza la UI del Stock (llama a función separada)
    updateStockDisplay();
}

/**
 * Actualiza la UI relacionada con el stock (texto y estado de botones).
 */
function updateStockDisplay() {
    const stockContainer = $("#product-stock-container");
    const stockDisplay = $("#product-stock-display");
    const stock = state.availableStock; // Usa el stock guardado (total o de sucursal)
    const btnPlus = $("#btn-quantity-plus");
    const btnMinus = $("#btn-quantity-minus");
    const inputQty = $("#product-quantity-input");
    const btnAdd = $("#btn-add-to-cart-detail");

    // Verifica que todos los elementos existan antes de modificarlos
    if (stockContainer && stockDisplay && btnPlus && btnMinus && inputQty && btnAdd) {
        if (stock > 0) { // Si hay stock
            stockDisplay.textContent = `${stock} unidades disponibles`;
            stockContainer.classList.remove("out-of-stock");
            // Habilita controles de cantidad
            btnPlus.disabled = false;
            btnMinus.disabled = false;
            inputQty.disabled = false;
            // Habilita "Añadir al carrito" SOLO SI también hay una talla seleccionada (o es Talla Única)
            btnAdd.disabled = !state.selectedVariation;
            btnAdd.textContent = "Añadir al carrito";
        } else { // Si no hay stock (stock es 0 o menos)
            stockDisplay.textContent = "AGOTADO";
            stockContainer.classList.add("out-of-stock");
            // Deshabilita todos los controles
            btnPlus.disabled = true;
            btnMinus.disabled = true;
            inputQty.disabled = true;
            btnAdd.disabled = true;
            btnAdd.textContent = "Sin stock";
        }
        stockContainer.style.display = "block"; // Muestra el contenedor de stock

        // Ajusta el valor del input si supera el stock actual o si el stock es 0
        if (parseInt(inputQty.value) > stock && stock > 0) {
            inputQty.value = stock; // No permitir seleccionar más que el stock
        } else if (stock === 0) {
            inputQty.value = 1; // Resetea a 1 si no hay stock (aunque estará deshabilitado)
        }
    } else {
        // Advierte si falta algún elemento esencial para la UI de stock
        console.warn("Faltan elementos HTML para mostrar el stock o los botones de cantidad/añadir.");
    }
}

/**
 * Añade listeners a las miniaturas de la galería.
 */
function setupImageGalleryListeners() {
  const thumbnails = $all(".product-gallery-thumbnails img");
  thumbnails.forEach(thumb => {
    thumb.addEventListener("click", () => {
      const mainImg = $("#product-image-main img");
      if(mainImg) mainImg.src = thumb.src; // Cambia la imagen principal
      // Actualiza cuál miniatura está activa
      thumbnails.forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
    });
  });
}

/**
 * Añade listeners a los botones de talla.
 */
function setupVariationListeners() {
  const variationButtons = $all(".btn-talla");
  variationButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      // Guarda la información de la variación seleccionada
      state.selectedVariation = {
          sku_variacion: btn.dataset.skuVariacion,
          talla: btn.dataset.talla,
          color: btn.dataset.color || '' // Asegura que color exista
      };
      // Actualiza visualmente qué botón está seleccionado
      variationButtons.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      // Oculta el mensaje de error de talla
      const variationErrorEl = $("#variation-error");
      if(variationErrorEl) variationErrorEl.style.display = "none";

      // Habilita el botón "Añadir al carrito" si hay stock disponible
      const btnAdd = $("#btn-add-to-cart-detail");
      if(btnAdd && state.availableStock > 0) {
          btnAdd.disabled = false;
      }

      // Actualiza la muestra de color si esta talla tiene un color específico
      const colorContainer = $("#product-color-container");
      if (btn.dataset.color && colorContainer) {
         const nombreColor = btn.dataset.color;
         const colorCSS = traducirColorACSS(nombreColor);
         const colorNameEl = $("#product-color-name");
         const colorSwatchEl = $("#product-color-swatch");
         if(colorNameEl) colorNameEl.textContent = nombreColor;
         if(colorSwatchEl) {
             colorSwatchEl.style.backgroundColor = colorCSS;
             // Ajusta borde para colores claros
             if (colorCSS.toLowerCase() === "white" || colorCSS.toLowerCase() === "beige" || colorCSS.toLowerCase() === "#ffffff") {
               colorSwatchEl.style.borderColor = "#999";
             } else { colorSwatchEl.style.borderColor = "#ccc"; }
         }
         colorContainer.style.display = "block"; // Muestra el color
      }
      // Opcional: Si la talla no tiene color propio, podrías decidir si ocultar
      // la sección de color o volver a mostrar el color base del producto.
      // else if (colorContainer) { /* Lógica para mostrar color base o nada */ }
    });
  });
}

/**
 * Añade listeners a los botones +/- y al input de cantidad.
 */
function setupQuantityListeners() {
  const btnMinus = $("#btn-quantity-minus");
  const btnPlus = $("#btn-quantity-plus");
  const input = $("#product-quantity-input");
  // Verifica que existan los elementos
  if(!btnMinus || !btnPlus || !input) {
      console.warn("Elementos del selector de cantidad no encontrados.");
      return;
  }

  // Botón '+'
  btnPlus.addEventListener("click", () => {
    const stock = state.availableStock; // Lee el stock actual
    hideStockError(); // Oculta errores previos
    try {
      let currentVal = parseInt(input.value, 10);
      if (isNaN(currentVal)) currentVal = 1;
      // Solo incrementa si es menor que el stock y menor que el límite (99)
      if (currentVal < stock && currentVal < 99) {
        input.value = currentVal + 1;
      } else {
        showStockError(stock); // Muestra error si se alcanza el límite de stock
      }
    } catch (e) { input.value = 1; } // Resetea a 1 en caso de error
  });

  // Botón '-'
  btnMinus.addEventListener("click", () => {
    hideStockError(); // Oculta errores al restar
    try {
      let currentVal = parseInt(input.value, 10);
      if (isNaN(currentVal)) currentVal = 1;
      // Solo decrementa si es mayor que 1
      if (currentVal > 1) {
        input.value = currentVal - 1;
      }
    } catch (e) { input.value = 1; } // Resetea a 1 en caso de error
  });

  // Input (al cambiar manualmente)
  input.addEventListener("change", () => {
    const stock = state.availableStock;
    hideStockError();
    try {
      let currentVal = parseInt(input.value, 10);
      // Corrige si no es número o es menor que 1
      if (isNaN(currentVal) || currentVal < 1) {
        input.value = 1;
        currentVal = 1; // Actualiza el valor para las siguientes validaciones
      }
      // Corrige si supera el stock disponible (y hay stock)
      if (stock > 0 && currentVal > stock) {
        input.value = stock;
        showStockError(stock);
      } else if (stock === 0) { // Si no hay stock, no debería permitir > 0 (resetea a 1, aunque estará disabled)
        input.value = 1;
      }
      // Corrige si supera el límite general (99)
      if (currentVal > 99) {
        input.value = 99;
      }
    } catch (e) { input.value = 1; } // Resetea a 1 en caso de error
  });
}

/**
 * Añade listener al botón "Añadir al carrito".
 * Valida talla, cantidad y stock antes de llamar a addItem.
 */
function setupAddToCartListener() {
  const btnAdd = $("#btn-add-to-cart-detail");
  if(!btnAdd){ console.warn("Botón 'Añadir al carrito' no encontrado."); return; }

  btnAdd.addEventListener("click", () => {
    hideStockError(); // Oculta errores previos

    // 1. Validar que se haya seleccionado una talla (o sea Talla Única)
    if (!state.selectedVariation) {
      const variationErrorEl = $("#variation-error");
      if(variationErrorEl) variationErrorEl.style.display = "block"; // Muestra error de talla
      return; // Detiene
    }

    // 2. Leer cantidad del input
    const quantityInput = $("#product-quantity-input");
    if(!quantityInput) { console.error("Input de cantidad no encontrado."); return;} // Chequeo extra
    const quantity = parseInt(quantityInput.value, 10);

    // 3. Validar cantidad (>= 1)
    if (isNaN(quantity) || quantity < 1) {
      alert("Por favor, selecciona una cantidad válida.");
      quantityInput.value = 1; // Resetea input
      return; // Detiene
    }

    // 4. Validar contra el stock disponible
    if (quantity > state.availableStock) {
      showStockError(state.availableStock); // Muestra error de stock
      return; // Detiene
    }

    // Si todo es válido:
    // 5. Obtener datos del producto y la variación seleccionada
    const { producto } = state.product; // 'producto' tiene toda la info base y de oferta
    const { sku_variacion, talla, color } = state.selectedVariation;

    // 6. Determinar el precio final a añadir al carrito
    const priceForCart = producto.precio_oferta !== null && producto.precio_oferta !== undefined
                         ? producto.precio_oferta
                         : producto.precio_producto;

    // 7. Crear el objeto para enviar a cart.js
    const itemToAdd = {
      id: producto.id_producto,
      name: producto.nombre_producto,
      price: priceForCart, // Usa el precio final (con o sin oferta)
      image: state.product.imagenes[0] || '../Public/imagenes/placeholder.jpg',
      sku: sku_variacion || producto.sku, // Usa SKU de variación o SKU base
      variation: { talla: talla, color: color || '' } // Pasa info de talla y color
    };

    // 8. Llamar a addItem (que se encarga de guardar y abrir el modal)
    addItem(itemToAdd, quantity);

    // 9. Feedback visual en el botón
    const btn = btnAdd; // Ya lo tenemos
    const prevText = btn.textContent;
    btn.textContent = "¡Añadido!";
    btn.disabled = true; // Deshabilita temporalmente
    setTimeout(() => {
      // Solo rehabilita si AÚN hay stock (podría haberse agotado con esta compra)
      // Recalcular el stock podría ser complejo aquí, así que asumimos que sigue habiendo
      // o confiamos en que `updateStockDisplay` lo corregirá si se recarga.
      // Por simplicidad, lo rehabilitamos si el stock inicial era > 0
      if(state.availableStock > 0){
        btn.textContent = prevText;
        btn.disabled = false;
      } else {
        btn.textContent = "Sin stock"; // Mantiene deshabilitado si se agotó
      }
      if(quantityInput) quantityInput.value = 1; // Resetea el input a 1
    }, 1000); // Después de 1 segundo
  });
}

// --- Funciones de Ayuda (Stock Error) ---
function showStockError(stock) {
  const errorMsg = $("#stock-error");
  const errorQty = $("#stock-error-qty");
  if(errorMsg && errorQty) {
    errorQty.textContent = stock; // Muestra cuánto stock queda
    errorMsg.style.display = "block"; // Muestra el mensaje
    clearTimeout(stockErrorTimeout); // Limpia timer anterior si existe
    // Oculta el mensaje después de 3 segundos
    stockErrorTimeout = setTimeout(() => { if(errorMsg) errorMsg.style.display = "none"; }, 3000);
  } else { console.warn("Elementos HTML para mostrar error de stock no encontrados.");}
}
function hideStockError() {
  clearTimeout(stockErrorTimeout); // Limpia timer si se estaba mostrando
  const errorMsg = $("#stock-error");
  if (errorMsg) errorMsg.style.display = "none"; // Oculta el mensaje
}

// --- Funciones de UI (Mostrar/Ocultar contenido principal) ---
function showError(message) {
  const loading = $("#product-loading"); const data = $("#product-data");
  const errorEl = $("#product-error"); const errorMsgEl = $("#product-error-message");
  if(loading) loading.style.display = "none"; // Oculta carga
  if(data) data.style.display = "none";    // Oculta contenido
  if(errorMsgEl) errorMsgEl.textContent = message; // Pone mensaje de error
  if(errorEl) errorEl.style.display = "block";    // Muestra bloque de error
}
function showContent() {
  console.log("[ShowContent Debug] showContent llamada."); // DEBUG
  const loading = $("#product-loading");
  const errorEl = $("#product-error");
  const dataContainer = $("#product-data"); // El div principal del producto

  console.log("[ShowContent Debug] Contenedor #product-data encontrado:", dataContainer); // DEBUG

  if(loading) loading.style.display = "none"; // Oculta carga
  if(errorEl) errorEl.style.display = "none";    // Oculta error (si estaba visible)

  // Comprueba si encontró el contenedor antes de cambiar el estilo
  if(dataContainer) {
    dataContainer.style.display = "grid"; // Cambia a 'grid' para mostrarlo
    console.log("[ShowContent Debug] Estilo de #product-data cambiado a 'grid'. ¿Se ve el producto?"); // DEBUG
  } else {
    // Si no encuentra el contenedor principal, muestra un error grave
    console.error("[ShowContent Debug] ¡ERROR CRÍTICO! No se encontró el contenedor #product-data para mostrar el producto.");
    showError("Error al intentar mostrar la información del producto."); // Notifica al usuario
  }
}

/**
 * --- NUEVO: Manejador para eventos de geolocalización ---
 * Vuelve a cargar los detalles si la sucursal cambia o se limpia después de la carga inicial.
 */
function handleBranchUpdate() {
    console.log("[Detalle Debug] Actualización de sucursal detectada. Recargando detalles...");
    // Vuelve a llamar a loadProductDetails para obtener el stock actualizado
    // para la nueva/ninguna sucursal detectada.
    loadProductDetails();
}