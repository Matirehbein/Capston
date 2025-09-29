// Public/js/productsStore.js
const PRODUCTS_EVT = 'products:changed';

async function fetchProducts() {
  try {
    const res = await fetch('/api/productos');
    return await res.json();
  } catch (e) {
    console.error('Error al cargar productos', e);
    return [];
  }
}

async function saveProduct(p) {
  const res = await fetch('/api/productos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(p)
  });
  return await res.json();
}

async function deleteProducts(ids) {
  await fetch('/api/productos', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
}

export const ProductsStore = {
  async getAll() { return await fetchProducts(); },
  async add(p) { 
    const saved = await saveProduct(p);
    window.dispatchEvent(new CustomEvent(PRODUCTS_EVT, { detail: { products: await fetchProducts() } }));
    return saved;
  },
  async removeByIds(ids=[]) {
    await deleteProducts(ids);
    window.dispatchEvent(new CustomEvent(PRODUCTS_EVT, { detail: { products: await fetchProducts() } }));
  },
  onChange(handler) {
    window.addEventListener(PRODUCTS_EVT, (e) => handler(e.detail.products));
  }
};
