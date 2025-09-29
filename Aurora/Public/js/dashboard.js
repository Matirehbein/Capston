// Public/js/dashboard.js
import { OrdersStore } from './ordersStore.js';

const $ = (s,r=document) => r.querySelector(s);

async function renderSummary(){
  const orders = await OrdersStore.getAll();

  const total = orders.length;
  const ingresos = orders.reduce((acc,o)=>acc+(o.total||0),0);
  const completados = orders.filter(o=>o.estado==='completado').length;
  const pendientes = total - completados;

  $('#ordersCount').textContent = total;
  $('#incomeTotal').textContent = `$${ingresos.toLocaleString('es-CL')}`;
  $('#doneCount').textContent = completados;
  $('#pendingCount').textContent = pendientes;
}

document.addEventListener('DOMContentLoaded', renderSummary);
OrdersStore.onChange(renderSummary);
