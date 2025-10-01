// Public/js/productos.js
import { ProductsStore } from './productsStore.js';

const $ = (s,r=document) => r.querySelector(s);

function row(p){
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td>${p.sku}</td>
    <td>${p.nombre}</td>
    <td>$${(p.precio||0).toLocaleString('es-CL')}</td>
    <td>${p.categoria}</td>
    <td>
      <button data-id="${p.id}" data-act="delete">🗑</button>
    </td>`;
  return tr;
}

async function renderTable(products){
  const tbody = $('#productsTable tbody');
  tbody.innerHTML = '';
  products.forEach(p => tbody.appendChild(row(p)));
}

async function render(){
  const products = await ProductsStore.getAll();
  await renderTable(products);
}

document.addEventListener('DOMContentLoaded', render);

$('#productsTable').addEventListener('click', async e=>{
  if(e.target.tagName !== 'BUTTON') return;
  const id = e.target.dataset.id;
  const act = e.target.dataset.act;
  if(act==='delete'){
    await ProductsStore.removeByIds([id]);
    await render();
  }
});

ProductsStore.onChange(render);
