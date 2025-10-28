// Public/js/colores.js (basado en tu theme.js)

const THEME_KEY = 'aurora_theme';
const DEFAULT_THEME = 'aurora';

export function applyTheme(name){
  const theme = name || localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
}

// aplica al cargar
applyTheme();

// sincroniza entre pestañas
window.addEventListener('storage', (e) => {
  if (e.key === THEME_KEY) applyTheme(e.newValue);
});

// Listener unificado para DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  
  // --- Lógica del Theme Picker ---
  const picker = document.querySelector('[data-theme-picker]');
  if (picker) { // Solo si estamos en la página de config
    const current = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
    const radio = picker.querySelector(`input[name="theme"][value="${current}"]`);
    if (radio) radio.checked = true;

    picker.addEventListener('change', (e) => {
      const el = e.target.closest('input[name="theme"]');
      if (!el) return;
      applyTheme(el.value);
    });
  }

  // --- Lógica del Carrusel (tu código original) ---
  const track = document.querySelector(".carousel-track");
  const slides = track ? Array.from(track.children) : [];
  const nextButton = document.querySelector(".carousel-btn.next");
  const prevButton = document.querySelector(".carousel-btn.prev");
  let currentIndex = 0;

  function updateCarousel() {
    if (track) { // Solo si existe el track
        track.style.transform = `translateX(-${currentIndex * 100}%)`;
    }
  }

  if (nextButton && prevButton && track && slides.length > 0) { // Solo si existe el carrusel
    nextButton.addEventListener("click", () => {
      currentIndex = (currentIndex + 1) % slides.length;
      updateCarousel();
    });

    prevButton.addEventListener("click", () => {
      currentIndex = (currentIndex - 1 + slides.length) % slides.length;
      updateCarousel();
    });

    // Auto-slide cada 5 segundos
    setInterval(() => {
      currentIndex = (currentIndex + 1) % slides.length;
      updateCarousel();
    }, 5000);
  }
});