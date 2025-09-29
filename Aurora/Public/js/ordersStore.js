// Public/js/ordersStore.js
const ORDERS_EVT = 'orders:changed';

async function fetchOrders() {
  try {
    const res = await fetch('/api/pedidos');
    return await res.json();
  } catch (e) {
    console.error('Error al cargar pedidos', e);
    return [];
  }
}

async function saveOrder(order) {
  const res = await fetch('/api/pedidos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(order)
  });
  return await res.json();
}

async function deleteOrders(ids) {
  await fetch('/api/pedidos', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids })
  });
}

async function putStatus(id, status) {
  await fetch(`/api/pedidos/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ estado: status })
  });
}

export const OrdersStore = {
  async getAll() { return await fetchOrders(); },
  async add(order) { 
    const saved = await saveOrder(order);
    window.dispatchEvent(new CustomEvent(ORDERS_EVT, { detail: { orders: await fetchOrders() } }));
    return saved;
  },
  async removeByIds(ids=[]) {
    await deleteOrders(ids);
    window.dispatchEvent(new CustomEvent(ORDERS_EVT, { detail: { orders: await fetchOrders() } }));
  },
  async updateStatus(id, status) {
    await putStatus(id, status);
    window.dispatchEvent(new CustomEvent(ORDERS_EVT, { detail: { orders: await fetchOrders() } }));
  },
  onChange(handler) {
    window.addEventListener(ORDERS_EVT, (e) => handler(e.detail.orders));
  }
};
