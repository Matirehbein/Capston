// ../Public/Js/navigation.js
import { updateCartBadge } from './cart.js'; // Asegúrate que la ruta a cart.js sea correcta

document.addEventListener('DOMContentLoaded', () => {
    // Llama a la función para actualizar el ícono del carrito
    updateCartBadge();
});

document.addEventListener('DOMContentLoaded', () => {
  const navItem = document.querySelector('.nav-item-with-megamenu');
  const megaMenu = navItem ? navItem.querySelector('.mega-menu') : null;
  let leaveTimeout; // Timer para el retraso al salir

  if (!navItem || !megaMenu) {
    // Si no se encuentran los elementos, no hacer nada
    return;
  }

  // --- Mostrar al entrar en el LI ---
  navItem.addEventListener('mouseenter', () => {
    clearTimeout(leaveTimeout); // Cancela cualquier timer de ocultación pendiente
    megaMenu.classList.add('visible');
  });

  // --- Ocultar al salir del LI (con retraso) ---
  navItem.addEventListener('mouseleave', () => {
    leaveTimeout = setTimeout(() => {
      megaMenu.classList.remove('visible');
    }, 200); // 200ms de retraso
  });

  // --- Mantener visible si el mouse entra EN el menú ---
  megaMenu.addEventListener('mouseenter', () => {
    clearTimeout(leaveTimeout); // Cancela la ocultación
  });

  // --- Ocultar si el mouse sale DEL menú ---
  megaMenu.addEventListener('mouseleave', () => {
    leaveTimeout = setTimeout(() => {
      megaMenu.classList.remove('visible');
    }, 200);
  });

});