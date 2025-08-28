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
