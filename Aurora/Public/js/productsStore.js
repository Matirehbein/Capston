// Public/js/productsStore.js
const PRODUCTS_KEY = 'aurora_products';
const PRODUCTS_EVT = 'products:changed';

function read() {
  try { return JSON.parse(localStorage.getItem(PRODUCTS_KEY) || '[]'); }
  catch { return []; }
}
function write(list) {
  localStorage.setItem(PRODUCTS_KEY, JSON.stringify(list));
  window.dispatchEvent(new CustomEvent(PRODUCTS_EVT, { detail: { products: list } }));
}

export const ProductsStore = {
  getAll() { return read(); },
  add(p) {
    const list = read();
    list.unshift(p);
    write(list);
  },
  removeByIds(ids = []) {
    const set = new Set(ids.map(x => String(x)));
    write(read().filter(p => !set.has(String(p.id))));
  },
  onChange(handler) {
    window.addEventListener(PRODUCTS_EVT, (e) => handler(e.detail.products));
    window.addEventListener('storage', (e) => {
      if (e.key === PRODUCTS_KEY) handler(read());
    });
  },
  seedIfEmpty() {
    if (read().length) return;
    write([
      { id: 'SKU-1001', nombre: 'Vestido Seda', categoria: 'Vestidos', stock: 3,  precio: 19990 },
      { id: 'SKU-1002', nombre: 'Blusa Drapeada', categoria: 'Blusas', stock: 12, precio: 29990 },
      { id: 'SKU-1003', nombre: 'Pantalón Palazzo', categoria: 'Pantalones', stock: 2, precio: 34990 },
    ]);
  }
};
