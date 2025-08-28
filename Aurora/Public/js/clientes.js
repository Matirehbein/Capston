// Public/js/clientes.js
const $ = (s, r=document) => r.querySelector(s);

const CLIENTES = [
  { id:'C-101', nombre:'Camila Rojas', email:'camila@mail.com', fono:'+56 9 3333 3333', last:'2025-08-23', spent:29990,  orders:1 },
  { id:'C-102', nombre:'Pedro Soto',   email:'pedro@mail.com',  fono:'+56 9 5555 5555', last:'2025-08-24', spent:39990,  orders:2 },
  { id:'C-103', nombre:'María Pérez',  email:'maria@mail.com',  fono:'+56 9 2222 2222', last:'2025-08-21', spent:259990, orders:5 }
];

// util: avatar con iniciales
function avatarFor(name){
  const div = document.createElement('div');
  div.className = 'avatar';
  const initials = (name||'?').split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase();
  div.textContent = initials;
  return div;
}

// tarjeta de cliente
function card(c){
  const art = document.createElement('article');
  art.className = 'client-card';

  const top = document.createElement('div');
  top.className = 'client-top';
  top.appendChild(avatarFor(c.nombre));

  const meta = document.createElement('div');
  meta.className = 'client-meta';

  const h3 = document.createElement('h3');
  h3.textContent = c.nombre;

  const p = document.createElement('p');
  p.textContent = c.email;

  const stats = document.createElement('span');
  stats.className = 'muted';
  stats.textContent = `${c.orders} pedidos · $${Number(c.spent||0).toLocaleString('es-CL')}`;

  meta.appendChild(h3);
  meta.appendChild(p);
  meta.appendChild(stats);

  art.appendChild(top);
  art.appendChild(meta);
  return art;
}

// renderizar los 3 clientes
function render(){
  const grid = $('#clientsGrid');
  grid.innerHTML = '';
  CLIENTES.forEach(c => grid.appendChild(card(c)));
}

document.addEventListener('DOMContentLoaded', render);
