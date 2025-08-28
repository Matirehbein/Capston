// Public/js/ordersStore.js
const ORDERS_KEY = 'aurora_orders';
const ORDERS_EVT = 'orders:changed';

/** ---- Helpers ---- */
function readOrders() {
  try { return JSON.parse(localStorage.getItem(ORDERS_KEY) || '[]'); }
  catch { return []; }
}
function writeOrders(list) {
  localStorage.setItem(ORDERS_KEY, JSON.stringify(list));
  // Notifica a la misma página
  window.dispatchEvent(new CustomEvent(ORDERS_EVT, { detail: { orders: list } }));
}

/** ---- API ---- */
export const OrdersStore = {
  getAll() {
    return readOrders();
  },
  add(order) {
    const list = readOrders();
    list.unshift(order); // más nuevo primero
    writeOrders(list);
  },
  removeByIds(ids = []) {
    if (!ids.length) return;
    const set = new Set(ids.map(n => String(n)));
    const list = readOrders().filter(o => !set.has(String(o.id)));
    writeOrders(list);
  },
  updateStatus(id, status) {
    const list = readOrders().map(o => (String(o.id) === String(id) ? { ...o, estado: status } : o));
    writeOrders(list);
  },
  /** suscríbete a cambios (misma pestaña) */
  onChange(handler) {
    window.addEventListener(ORDERS_EVT, (e) => handler(e.detail.orders));
    // cambios desde OTRAS pestañas
    window.addEventListener('storage', (e) => {
      if (e.key === ORDERS_KEY) handler(readOrders());
    });
  },
  /** si NO hay pedidos, deja algunos de ejemplo (una sola vez) */
  seedIfEmpty() {
    const has = readOrders();
    if (has.length) return;
    const seed = [
      { id: 10241, cliente: 'María P.', fecha: '2025-08-21', estado: 'preparando', total: 49990, items: ['Vestido Seda — 1u — $19.990', 'Blusa — 1u — $29.990'] },
      { id: 10240, cliente: 'Jorge S.', fecha: '2025-08-21', estado: 'despachado', total: 32480, items: ['Pantalón — 1u — $32.480'] },
      { id: 10239, cliente: 'Camila R.', fecha: '2025-08-20', estado: 'pendiente', total: 21990, items: ['Falda — 1u — $21.990'] },
    ];
    writeOrders(seed);
  }
};
