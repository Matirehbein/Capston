// Public/js/productos.js
import { ProductsStore } from './productsStore.js';

const $  = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => Array.from(r.querySelectorAll(s));
const CLP = n => `$${Number(n||0).toLocaleString('es-CL')}`;

function renderRow(p){
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><input type="checkbox" class="row-check"></td>
    <td>${p.id}</td>
    <td>${p.nombre}</td>
    <td>${p.categoria}</td>
    <td>${p.stock}</td>
    <td>${CLP(p.precio)}</td>
  `;
  return tr;
}
function renderTable(products){
  const tbody = $('#productsTable tbody');
  tbody.innerHTML = '';
  products.forEach(p => tbody.appendChild(renderRow(p)));
}
function applyFilters(){
  const txt = $('#searchInput')?.value.trim().toLowerCase() || '';
  const activeCat = $('.chip.active')?.dataset.cat || 'todas';
  $$('#productsTable tbody tr').forEach(tr => {
    const rowText = tr.innerText.toLowerCase();
    const cat = tr.children[3].textContent.trim();
    const matchTxt = !txt || rowText.includes(txt);
    const matchCat = activeCat === 'todas' || activeCat === cat;
    tr.style.display = (matchTxt && matchCat) ? '' : 'none';
  });
}

document.addEventListener('DOMContentLoaded', () => {
  // Toggle sidebar
  $('#sidebarToggle')?.addEventListener('click', ()=> $('#adminSidebar').classList.toggle('open'));

  // Datos demo si está vacío
  ProductsStore.seedIfEmpty();

  // Render inicial
  renderTable(ProductsStore.getAll());
  applyFilters();

  // Filtros
  $$('.chip').forEach(c => c.addEventListener('click', () => {
    $$('.chip').forEach(x => x.classList.remove('active'));
    c.classList.add('active');
    applyFilters();
  }));
  $('#searchInput')?.addEventListener('input', applyFilters);

  // Seleccionar todo
  const selectAll = $('#selectAllProd');
  selectAll?.addEventListener('change', () => {
    $$('.row-check').forEach(cb => cb.checked = selectAll.checked);
  });

  // Eliminar en lote
  $('#deleteProdBulk')?.addEventListener('click', () => {
    const ids = $$('.row-check:checked').map(cb => cb.closest('tr').children[1].textContent.trim());
    if (!ids.length) return;
    ProductsStore.removeByIds(ids);
  });

  // Modal nuevo
  const modal = $('#newProdModal');
  const openNew = ()=> modal.classList.add('open');
  const closeNew = ()=> modal.classList.remove('open');

  $('#newProdBtn')?.addEventListener('click', openNew);
  $('#closeNewProd')?.addEventListener('click', closeNew);
  $('#cancelNewProd')?.addEventListener('click', closeNew);
  modal?.addEventListener('click', (e)=>{ if(e.target.id==='newProdModal') closeNew(); });

  // Guardar nuevo producto
  $('#newProdForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const p = {
      id:        $('#pSku').value.trim(),
      nombre:    $('#pNombre').value.trim(),
      categoria: $('#pCategoria').value.trim() || 'General',
      stock:     parseInt($('#pStock').value,10) || 0,
      precio:    parseInt($('#pPrecio').value,10) || 0,
    };
    if (!p.id || !p.nombre) return;
    ProductsStore.add(p);
    e.target.reset();
    closeNew();
  });

  // Re-render ante cambios (misma u otra pestaña)
  ProductsStore.onChange((products) => {
    renderTable(products);
    applyFilters();
  });
  // dentro del submit de #newProdForm:
const p = {
  id:        $('#pSku').value.trim(),
  nombre:    $('#pNombre').value.trim(),
  categoria: $('#pCategoria').value.trim() || 'General',
  stock:     parseInt($('#pStock').value,10) || 0,
  precio:    parseInt($('#pPrecio').value,10) || 0,
  imagen:    $('#pImagen')?.value.trim() || ''   // << nuevo
};

});
