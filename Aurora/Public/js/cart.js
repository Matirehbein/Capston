// ../Public/js/cart.js
export const STORAGE_KEY = "aurora_cart_v1";

export function formatCLP(value) {
  try {
    return Number(value).toLocaleString("es-CL", {
      style: "currency",
      currency: "CLP",
      maximumFractionDigits: 0
    });
  } catch {
    return `$${value}`;
  }
}

export function getCart() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveCart(cart) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
}

export function addItem(product, qty = 1) {
  const cart = getCart();
  const idx = cart.findIndex(it => it.id === product.id);
  if (idx >= 0) {
    cart[idx].qty += qty;
  } else {
    cart.push({
      id: product.id,
      sku: product.sku || null,
      name: product.name,
      price: Number(product.price) || 0,
      image: product.image || "../Public/imagenes/placeholder.jpg",
      qty: Number(qty) || 1
    });
  }
  saveCart(cart);
  return cart;
}

export function removeItem(id) {
  const cart = getCart().filter(it => it.id !== id);
  saveCart(cart);
  return cart;
}

export function setQty(id, qty) {
  const cart = getCart();
  const item = cart.find(it => it.id === id);
  if (!item) return cart;
  item.qty = Math.max(1, Number(qty) || 1);
  saveCart(cart);
  return cart;
}

export function totalItems() {
  return getCart().reduce((acc, it) => acc + it.qty, 0);
}

export function totalPrice() {
  return getCart().reduce((acc, it) => acc + it.qty * it.price, 0);
}
