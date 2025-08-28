// Public/js/pedidos.js
import { OrdersStore } from './ordersStore.js';

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));

function titleCase(s){ return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }
function badgeFor(status){
  const span = document.createElement('span');
  span.className = 'badge';
  if (status === 'despachado') span.classList.add('ok');
  else if (status === 'pendiente') span.classList.add('warn');
  else if (status === 'preparando') span.classList.add('soft');
  span.textContent = titleCase(status.replace('-', ' '));
  return span;
}
function nextOrderId(){
  const ids = OrdersStore.getAll().map(o => Number(o.id)).filter(n => !isNaN(n));
  const max = ids.length ? Math.max(...ids) : 10000;
  return max + 1;
}
function renderRow(o){
  const tr = document.createElement('tr');
  tr.dataset.status = o.estado;
  if (o.items?.length) tr.dataset.items = JSON.stringify(o.items);
  tr.innerHTML = `
    <td><input type="checkbox" class="row-check"></td>
    <td>${o.id}</td>
    <td>${o.cliente}</td>
    <td>${new Date(o.fecha).toLocaleDateString()}</td>
    <td></td>
    <td>$${(o.total||0).toLocaleString('es-CL')}</td>
    <td><button class="btn-sm alt view-btn">Ver</button></td>
  `;
  tr.children[4].appendChild(badgeFor(o.estado));
  wireRow(tr);
  return tr;
}
function wireRow(tr){
  tr.querySelector('.view-btn').addEventListener('click', () => {
    $('#modalTitle').textContent = 'Pedido #' + tr.children[1].textContent.trim();
    $('#mCliente').textContent   = tr.children[2].textContent.trim();
    $('#mFecha').textContent     = tr.children[3].textContent.trim();
    $('#mEstado').textContent    = tr.children[4].innerText.trim();
    $('#mTotal').textContent     = tr.children[5].textContent.trim();
    const items = tr.dataset.items ? JSON.parse(tr.dataset.items) : [];
    const ul = $('#mItems'); ul.innerHTML = items.length ? '' : '<li>(sin detalle)</li>';
    items.forEach(t => { const li = document.createElement('li'); li.textContent = t; ul.appendChild(li); });
    $('#orderModal').classList.add('open');
  });
}
function refreshFilters(){
  const active = $('.chip.active')?.dataset.status || 'todos';
  const txt    = $('#searchInput')?.value.trim().toLowerCase() || '';
  $$('#ordersTable tbody tr').forEach(tr => {
    const matchesStatus = active === 'todos' || tr.dataset.status === active;
    const matchesText   = !txt || tr.innerText.toLowerCase().includes(txt);
    tr.style.display = (matchesStatus && matchesText) ? '' : 'none';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // sidebar
  $('#sidebarToggle')?.addEventListener('click', ()=> $('#adminSidebar').classList.toggle('open'));

  // chips
  $$('.chip').forEach(chip => chip.addEventListener('click', () => {
    $$('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    refreshFilters();
  }));
  // buscar
  $('#searchInput')?.addEventListener('input', refreshFilters);

  // render inicial
  OrdersStore.seedIfEmpty();
  const tbody = $('#ordersTable tbody');
  tbody.innerHTML = '';
  OrdersStore.getAll().forEach(o => tbody.appendChild(renderRow(o)));
  refreshFilters();

  // seleccionar todo
  const selectAll = $('#selectAll');
  selectAll?.addEventListener('change', () => {
    $$('.row-check').forEach(cb => cb.checked = selectAll.checked);
  });

  // acciones en lote
  $('#applyBulk')?.addEventListener('click', () => {
    const newStatus = $('#bulkStatus').value;
    if (!newStatus) return;
    const selected = $$('.row-check:checked').map(cb => cb.closest('tr'));
    selected.forEach(tr => {
      const id = tr.children[1].textContent.trim();
      OrdersStore.updateStatus(id, newStatus);
    });
  });

  $('#deleteBulk')?.addEventListener('click', () => {
    const ids = $$('.row-check:checked').map(cb => cb.closest('tr').children[1].textContent.trim());
    OrdersStore.removeByIds(ids);
  });

  // modal detalle: cerrar
  $('#closeModal')?.addEventListener('click', ()=> $('#orderModal').classList.remove('open'));
  $('#orderModal')?.addEventListener('click', (e)=>{ if(e.target.id==='orderModal') $('#orderModal').classList.remove('open'); });

  // nuevo pedido
  const newOrderModal = $('#newOrderModal');
  const openNew  = ()=> newOrderModal.classList.add('open');
  const closeNew = ()=> newOrderModal.classList.remove('open');

  $('#newOrderBtn')?.addEventListener('click', openNew);
  $('#closeNewOrder')?.addEventListener('click', closeNew);
  $('#cancelNewOrder')?.addEventListener('click', closeNew);
  newOrderModal?.addEventListener('click', (e)=>{ if(e.target.id==='newOrderModal') closeNew(); });

  $('#newOrderForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const order = {
      id:      nextOrderId(),
      cliente: $('#fCliente').value.trim(),
      fecha:   $('#fFecha').value,
      estado:  $('#fEstado').value,
      total:   parseInt($('#fTotal').value,10) || 0,
      items:   ($('#fItems').value.trim() ? $('#fItems').value.split('\n').map(s=>s.trim()).filter(Boolean) : [])
    };
    OrdersStore.add(order);
    closeNew();
    e.target.reset();
  });

  // re-render ante cualquier cambio (propio u otra pestaña)
  OrdersStore.onChange((orders) => {
    const tbody = $('#ordersTable tbody');
    tbody.innerHTML = '';
    orders.forEach(o => tbody.appendChild(renderRow(o)));
    refreshFilters();
  });
});
