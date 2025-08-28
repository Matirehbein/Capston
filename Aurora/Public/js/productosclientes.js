// Public/js/storefront-products.js
import { ProductsStore } from './productsStore.js';

const $ = (s, r = document) => r.querySelector(s);
const CLP = n => `$${Number(n || 0).toLocaleString('es-CL')}`;
const PLACEHOLDER = 'https://via.placeholder.com/480x360?text=Producto';

// Mantén http/https/data tal cual; normaliza *solamente* rutas locales
function normalizeImg(raw) {
  if (!raw) return '';
  const v = raw.trim();
  if (/^(https?:)?\/\//i.test(v) || /^data:image\//i.test(v)) return v; // externa/base64
  // Esta página vive en /src/productos.html → subimos un nivel para Public/
  let p = v.replace(/^(\.\/)+/, '').replace(/^\/+/, '');
  if (/^Public\//i.test(p))       return `../${p}`;
  if (/^imagenes\//i.test(p))     return `../Public/${p}`;
  if (!/\/./.test(p))             return `../Public/imagenes/${p}`; // sólo nombre.ext
  return `../${p}`;
}

// Carga segura con pre-check; devuelve un <img> listo
function buildImg(src, altText) {
  const img = document.createElement('img');
  img.alt = altText || 'Producto';
  img.loading = 'lazy';
  img.referrerPolicy = 'no-referrer';
  img.crossOrigin = 'anonymous';

  const test = new Image();
  test.referrerPolicy = 'no-referrer';
  test.crossOrigin = 'anonymous';

  // si carga ok, usamos src; si no, usamos placeholder
  test.onload = () => { img.src = src; };
  test.onerror = () => { img.src = PLACEHOLDER; };
  test.src = src || PLACEHOLDER;

  return img;
}

function productCard(p) {
  const card = document.createElement('article');
  card.className = 'producto'; // usa tus estilos existentes

  const src = normalizeImg(p.imagen || '');
  const img = buildImg(src, p.nombre);

  const title = document.createElement('h3');
  title.textContent = p.nombre || 'Producto';

  const price = document.createElement('p');
  price.className = 'producto-precio';
  price.textContent = CLP(p.precio || 0);

  const btn = document.createElement('button');
  btn.className = 'btn';
  const sinStock = (p.stock || 0) <= 0;
  btn.textContent = sinStock ? 'Agotado' : 'Añadir al carrito';
  btn.disabled = sinStock;
  btn.dataset.sku = p.id;

  card.appendChild(img);
  card.appendChild(title);
  card.appendChild(price);
  card.appendChild(btn);
  return card;
}

function renderList(products) {
  const grid = $('#store-products-grid');
  if (!grid) return;
  grid.innerHTML = '';
  products.forEach(p => grid.appendChild(productCard(p)));
}

function wireCart() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn || !btn.dataset.sku || btn.disabled) return;
    const sku = btn.dataset.sku;
    try {
      const cart = JSON.parse(localStorage.getItem('aurora_cart') || '[]');
      const item = cart.find(i => i.id === sku);
      if (item) item.qty += 1; else cart.push({ id: sku, qty: 1 });
      localStorage.setItem('aurora_cart', JSON.stringify(cart));
      btn.textContent = 'Añadido ✓';
      setTimeout(() => btn.textContent = 'Añadir al carrito', 900);
    } catch {}
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // ProductsStore.seedIfEmpty(); // <- déjalo comentado si ya usas el admin
  renderList(ProductsStore.getAll());
  wireCart();
  ProductsStore.onChange(renderList);
});
