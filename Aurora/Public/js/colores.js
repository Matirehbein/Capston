// Public/js/theme.js
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

// soporte automático para la página de configuración (si existe picker)
document.addEventListener('DOMContentLoaded', ()=>{
  const picker = document.querySelector('[data-theme-picker]');
  if (!picker) return;

  const current = localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
  const radio = picker.querySelector(`input[name="theme"][value="${current}"]`);
  if (radio) radio.checked = true;

  picker.addEventListener('change', (e) => {
    const el = e.target.closest('input[name="theme"]');
    if (!el) return;
    applyTheme(el.value);
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const track = document.querySelector(".carousel-track");
  const slides = Array.from(track.children);
  const nextButton = document.querySelector(".carousel-btn.next");
  const prevButton = document.querySelector(".carousel-btn.prev");
  let currentIndex = 0;

  function updateCarousel() {
    track.style.transform = `translateX(-${currentIndex * 100}%)`;
  }

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
});