/*
 * cantidad.js — Botones − / + de la cantidad en la página de producto.
 * Cambian el número y avisan para recotizar.
 */
document.querySelectorAll("[data-cant]").forEach((b) => b.addEventListener("click", () => {
  const campo = document.getElementById("cantidad");
  campo.value = Math.min(50, Math.max(1, Number(campo.value) + Number(b.dataset.cant)));
  campo.dispatchEvent(new Event("input", { bubbles: true }));
}));
