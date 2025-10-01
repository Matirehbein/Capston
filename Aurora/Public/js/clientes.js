// Public/js/clientes.js
const $ = (s, r=document) => r.querySelector(s);

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
  stats.textContent = `${c.orders||0} pedidos · $${Number(c.spent||0).toLocaleString('es-CL')}`;

  meta.appendChild(h3);
  meta.appendChild(p);
  meta.appendChild(stats);

  art.appendChild(top);
  art.appendChild(meta);
  return art;
}

// renderizar clientes desde API
async function render(){
  const grid = $('#clientsGrid');
  grid.innerHTML = '<p>Cargando clientes...</p>';
  try {
    const res = await fetch('/api/clientes');
    const clientes = await res.json();
    grid.innerHTML = '';
    clientes.forEach(c => grid.appendChild(card(c)));
  } catch (err) {
    console.error('Error cargando clientes', err);
    grid.innerHTML = '<p>Error al cargar clientes.</p>';
  }
}

document.addEventListener('DOMContentLoaded', render);
