const API_BACKEND = "http://localhost:5000"; // o la URL donde corre Flask

const ctx = document.getElementById("growthChart").getContext("2d");
let growthChart = null;

function renderGrowthChart(labels, ventas, pedidos, clientes) {
  if (growthChart) growthChart.destroy();

  growthChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Ventas",
          data: ventas,
          borderColor: "#6c5ce7",
          borderWidth: 4,
          tension: 0.4,
        },
        {
          label: "Pedidos",
          data: pedidos,
          borderColor: "#00b894",
          borderWidth: 4,
          tension: 0.4,
        },
        {
          label: "Clientes registrados",
          data: clientes,
          borderColor: "#d63031",
          borderWidth: 4,
          tension: 0.4,
        },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
      plugins: {
        legend: { labels: { font: { size: 14 } } }
      }
    }
  });
}

async function loadRange(range) {
  try {
    const res = await fetch(`${API_BACKEND}/api/dashboard/crecimiento?range=${range}`, {
      credentials: "include" // para que mande la cookie de sesión
    });
    const data = await res.json();
    if (data.error) {
      console.error("API error:", data.error);
      return;
    }
    renderGrowthChart(data.labels, data.ventas, data.pedidos, data.clientes);
  } catch (err) {
    console.error("Error cargando datos del gráfico:", err);
  }
}

// Botones de filtro (diario/semanal/mensual)
document.querySelectorAll(".growth-filters button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelector(".growth-filters .active")?.classList.remove("active");
    btn.classList.add("active");
    loadRange(btn.dataset.range);
  });
});

// Carga inicial
loadRange("daily");
