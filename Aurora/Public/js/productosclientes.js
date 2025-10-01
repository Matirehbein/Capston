// Public/js/productosclientes.js
import { ProductsStore } from './productsStore.js';

const $ = (s,r=document) => r.querySelector(s);

function card(p){
  const art = document.createElement('article');
  art.className = 'product-card';
  art.innerHTML = `
    <img src="${p.url_imagen}" alt="${p.nombre}">
    <h3>${p.nombre}</h3>
    <p class="price">$${(p.precio||0).toLocaleString('es-CL')}</p>
    <button data-id="${p.id}">Agregar al carrito</button>`;
  return art;
}

async function renderList(products){
  const grid = $('#productsGrid');
  grid.innerHTML = '';
  products.forEach(p => grid.appendChild(card(p)));
}

function wireCart(){
  $('#productsGrid').addEventListener('click', e=>{
    if(e.target.tagName !== 'BUTTON') return;
    const id = e.target.dataset.id;
    alert(`Producto ${id} agregado al carrito (aquí iría la lógica de carrito).`);
  });
}

document.addEventListener('DOMContentLoaded', async ()=>{
  const products = await ProductsStore.getAll();
  await renderList(products);
  wireCart();
});

ProductsStore.onChange(renderList);
