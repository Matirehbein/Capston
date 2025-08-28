// Public/js/dashboard.js
import { OrdersStore } from './ordersStore.js';

const $ = (s, r=document) => r.querySelector(s);

function formatCLP(n){ return `$ ${Number(n||0).toLocaleString('es-CL')}`; }

function renderPendientes(orders){
  const pendientes = orders.filter(o => o.estado === 'pendiente' || o.estado === 'preparando').length;
  const el = $('#kpi-pendientes');
  if (el) el.textContent = pendientes.toString();
}

function renderRecientes(orders){
  const tbody = $('#recent-orders-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  orders.slice(0,3).forEach(o => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${o.id}</td>
      <td>${o.cliente}</td>
      <td>${new Date(o.fecha).toLocaleDateString()}</td>
      <td>${o.estado}</td>
      <td>${formatCLP(o.total)}</td>
    `;
    tbody.appendChild(tr);
  });
}

// (Opcional) Ventas del día: suma totales con fecha de hoy
function renderVentasHoy(orders){
  const today = new Date(); today.setHours(0,0,0,0);
  const sum = orders
    .filter(o => { const d=new Date(o.fecha); d.setHours(0,0,0,0); return d.getTime()===today.getTime(); })
    .reduce((acc,o)=>acc+(o.total||0),0);
  const el = $('#kpi-ventas');
  if (el) el.textContent = formatCLP(sum);
}

document.addEventListener('DOMContentLoaded', () => {
  OrdersStore.seedIfEmpty();
  const orders = OrdersStore.getAll();
  renderPendientes(orders);
  renderRecientes(orders);
  renderVentasHoy(orders); // quítalo si prefieres número fijo

  OrdersStore.onChange((orders) => {
    renderPendientes(orders);
    renderRecientes(orders);
    renderVentasHoy(orders);
  });
});

