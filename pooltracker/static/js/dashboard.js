(function () {
  async function loadTrends() {
    const response = await fetch("/api/trends", { headers: { Accept: "application/json" } });
    if (!response.ok) {
      console.error("Failed to load trend data", response.status);
      return;
    }
    const data = await response.json();
    renderCharts(data);
  }

  function renderCharts(data) {
    const additionLines = data.additions.map((addition) => ({
      type: "line",
      xMin: addition.timestamp,
      xMax: addition.timestamp,
      borderColor: "#c0392b",
      borderWidth: 1,
      borderDash: [4, 4],
      label: {
        display: addition.items.length > 0,
        content: addition.items.map((i) => `${i.label} ${i.amount}${i.unit}`).join(", "),
        position: "start",
        rotation: 90,
        font: { size: 9 },
        backgroundColor: "rgba(192,57,43,0.85)",
        color: "#fff",
      },
    }));

    document.querySelectorAll("canvas[data-field]").forEach((canvas) => {
      const field = canvas.dataset.field;
      const points = data.readings
        .filter((r) => r[field] !== null && r[field] !== undefined)
        .map((r) => ({ x: r.timestamp, y: r[field] }));

      new Chart(canvas, {
        type: "line",
        data: {
          datasets: [
            {
              data: points,
              borderColor: "#0b6e99",
              backgroundColor: "rgba(11,110,153,0.1)",
              tension: 0.25,
              pointRadius: 3,
              fill: true,
            },
          ],
        },
        options: {
          responsive: true,
          plugins: {
            legend: { display: false },
            annotation: { annotations: additionLines },
          },
          scales: {
            x: {
              type: "time",
              time: { unit: "day" },
            },
            y: { beginAtZero: false },
          },
        },
      });
    });
  }

  loadTrends();
})();
