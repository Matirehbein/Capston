// ../Public/js/detalle_producto.js

// Importamos las funciones que necesitamos del carrito
import { addItem, formatCLP } from "./cart.js";

const API_BASE = "http://localhost:5000";
const $ = (s) => document.querySelector(s);
const $all = (s) => document.querySelectorAll(s);

// Estado global para la página de detalle
const state = {
  product: null,
  selectedVariation: null, // Guardará la variación (talla) seleccionada
};

/**
 * Función principal que se ejecuta al cargar la página
 */
document.addEventListener("DOMContentLoaded", () => {
  loadProductDetails();
  setupAddToCartListener();
});

/**
 * 1. Lee el ID de la URL
 * 2. Llama a la API de Flask
 * 3. Renderiza el producto o muestra un error
 */
// Reemplaza ESTA FUNCIÓN COMPLETA en detalle_producto.js

// Reemplaza ESTA FUNCIÓN COMPLETA en detalle_producto.js

// Reemplaza ESTA FUNCIÓN COMPLETA en detalle_producto.js

async function loadProductDetails() {

  // 🔽 ¡AQUÍ ESTÁ EL CAMBIO! 🔽
  // Ya no usamos URLSearchParams, leemos el "hash"
  
  // 1. Lee el hash (ej: "#id=5")
  const hash = window.location.hash;
  
  // 2. Quita el "#id=" para obtener solo el número "5"
  const idProducto = hash.replace("#id=", "");

  if (!idProducto) {
    showError("No se especificó ningún producto.");
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/producto/${idProducto}`);
    
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error("Producto no encontrado.");
      }
      throw new Error(`Error ${res.status}: No se pudo conectar al servidor.`);
    }

    const data = await res.json();
    
    state.product = data;
    
    renderProduct(data);
    showContent();

  } catch (err) {
    console.error("Error al cargar producto:", err);
    showError(err.message);
  }
}

/**
 * Rellena el HTML con los datos del producto obtenidos de la API
 */
function renderProduct(data) {
  const { producto, imagenes, variaciones } = data;

  // 1. Título de la página
  document.title = `Aurora | ${producto.nombre_producto}`;

  // 2. Información básica
  $("#product-name").textContent = producto.nombre_producto;
  $("#product-sku").textContent = producto.sku;
  $("#product-price").textContent = formatCLP(producto.precio_producto);
  $("#product-description").textContent = producto.descripcion_producto || "No hay descripción disponible.";

  // 3. Galería de Imágenes
  const mainImageContainer = $("#product-image-main");
  const thumbnailsContainer = $("#product-thumbnails");
  
  mainImageContainer.innerHTML = `<img src="${imagenes[0] || '../Public/imagenes/placeholder.jpg'}" alt="${producto.nombre_producto}">`;
  
  thumbnailsContainer.innerHTML = imagenes.map((img, index) => `
    <img src="${img}" alt="Miniatura ${index + 1}" class="${index === 0 ? 'active' : ''}" data-index="${index}">
  `).join("");
  
  setupImageGalleryListeners();

  // 4. Variaciones (Tallas)
  const tallasContainer = $("#product-tallas");
  if (variaciones.length > 0) {
    tallasContainer.innerHTML = variaciones.map(v => `
      <button class="btn-talla" 
              data-sku-variacion="${v.sku_variacion}" 
              data-talla="${v.talla}" 
              data-color="${v.color || ''}">
        ${v.talla}
      </button>
    `).join("");
    setupVariationListeners();
  } else {
    // Si no hay tallas (ej. Talla Única), seleccionamos el producto base
    tallasContainer.innerHTML = `<p>Talla Única</p>`;
    state.selectedVariation = {
      sku_variacion: producto.sku,
      talla: "Única",
      color: ""
    };
  }
}

/**
 * Añade listeners a las miniaturas para cambiar la imagen principal
 */
function setupImageGalleryListeners() {
  const thumbnails = $all(".product-gallery-thumbnails img");
  thumbnails.forEach(thumb => {
    thumb.addEventListener("click", () => {
      // Actualiza imagen principal
      const mainImage = $("#product-image-main img");
      mainImage.src = thumb.src;
      
      // Actualiza clase 'active'
      thumbnails.forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
    });
  });
}

/**
 * Añade listeners a los botones de talla
 */
function setupVariationListeners() {
  const variationButtons = $all(".btn-talla");
  variationButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      // Guarda la variación seleccionada en el estado
      state.selectedVariation = btn.dataset;
      
      // Actualiza clase 'selected'
      variationButtons.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");

      // Oculta error si estaba visible
      $("#variation-error").style.display = "none";
    });
  });
}

/**
 * Configura el listener para el botón "Añadir al carrito"
 */
function setupAddToCartListener() {
  $("#btn-add-to-cart-detail").addEventListener("click", () => {
    // 1. Validar que se haya seleccionado una variación (talla)
    if (!state.selectedVariation) {
      $("#variation-error").style.display = "block";
      return;
    }
    
    // 2. Obtener los datos del producto y la variación
    const { producto } = state.product;
    const { skuVariacion, talla } = state.selectedVariation;

    // 3. Crear el objeto para el carrito
    const itemToAdd = {
      id: producto.id_producto,
      name: producto.nombre_producto,
      price: producto.precio_producto,
      image: state.product.imagenes[0] || '../Public/imagenes/placeholder.jpg',
      sku: skuVariacion, // Usamos el SKU específico de la variación
      variation: { talla: talla } // Añadimos info extra de la variación
    };
    
    // 4. Añadir al carrito (usando la función de cart.js)
    addItem(itemToAdd, 1);
    
    // 5. Feedback visual
    const btn = $("#btn-add-to-cart-detail");
    const prevText = btn.textContent;
    btn.textContent = "¡Añadido!";
    btn.disabled = true;
    setTimeout(() => {
      btn.textContent = prevText;
      btn.disabled = false;
    }, 1000);
  });
}

// --- Funciones de UI (Mostrar/Ocultar estados) ---

function showError(message) {
  $("#product-loading").style.display = "none";
  $("#product-data").style.display = "none";
  $("#product-error-message").textContent = message;
  $("#product-error").style.display = "block";
}

function showContent() {
  $("#product-loading").style.display = "none";
  $("#product-error").style.display = "none";
  $("#product-data").style.display = "grid"; // 'grid' para que tome el estilo CSS
}