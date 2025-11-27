const ctx = document.getElementById("growthChart").getContext("2d");

const dataRanges = {
  daily: {
    labels: ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
    ventas: [20, 30, 40, 35, 50, 65, 70],
    pedidos: [15, 20, 22, 19, 30, 34, 40],
    clientes: [5, 4, 7, 6, 9, 10, 12]
  },

  weekly: {
    labels: ["Semana 1", "Semana 2", "Semana 3", "Semana 4"],
    ventas: [240, 310, 380, 450],
    pedidos: [160, 210, 260, 300],
    clientes: [30, 45, 55, 70]
  },

  monthly: {
    labels: ["Ene", "Feb", "Mar", "Abr", "May", "Jun"],
    ventas: [900, 1100, 1200, 1400, 1600, 1750],
    pedidos: [650, 700, 850, 900, 1050, 1150],
    clientes: [120, 150, 170, 210, 260, 300]
  },
};

let growthChart;

function createGrowthChart(range) {
  const data = dataRanges[range];

  if (growthChart) growthChart.destroy();

  growthChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Ventas",
          data: data.ventas,
          borderColor: "#6c5ce7",
          borderWidth: 4,
          tension: 0.4,
        },
        {
          label: "Pedidos",
          data: data.pedidos,
          borderColor: "#00b894",
          borderWidth: 4,
          tension: 0.4,
        },
        {
          label: "Clientes registrados",
          data: data.clientes,
          borderColor: "#d63031",
          borderWidth: 4,
          tension: 0.4,
        },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
        }
      },
      plugins: {
        legend: {
          labels: { font: { size: 14 } }
        }
      }
    }
  });
}

document.querySelectorAll(".growth-filters button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelector(".growth-filters .active")?.classList.remove("active");
    btn.classList.add("active");

    createGrowthChart(btn.dataset.range);
  });
});

createGrowthChart("daily");
