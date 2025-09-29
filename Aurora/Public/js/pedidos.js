// Public/js/pedidos.js
import { OrdersStore } from './ordersStore.js';

const $ = (s,r=document) => r.querySelector(s);

function row(o){
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${o.id}</td>
    <td>${o.cliente}</td>
    <td>${o.producto}</td>
    <td>$${(o.total||0).toLocaleString('es-CL')}</td>
    <td>${o.estado}</td>
    <td>
      <button data-id="${o.id}" data-act="done">✔</button>
      <button data-id="${o.id}" data-act="delete">🗑</button>
    </td>`;
  return tr;
}

async function render(){
  const tbody = $('#ordersTable tbody');
  tbody.innerHTML = '<tr><td colspan="6">Cargando...</td></tr>';
  const orders = await OrdersStore.getAll();
  tbody.innerHTML = '';
  orders.forEach(o => tbody.appendChild(row(o)));
}

document.addEventListener('DOMContentLoaded', render);

$('#ordersTable').addEventListener('click', async e => {
  if(e.target.tagName !== 'BUTTON') return;
  const id = e.target.dataset.id;
  const act = e.target.dataset.act;
  if(act === 'done'){
    await OrdersStore.updateStatus(id, 'completado');
  } else if(act === 'delete'){
    await OrdersStore.removeByIds([id]);
  }
  await render();
});

OrdersStore.onChange(render);
