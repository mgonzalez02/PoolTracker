(function () {
  const charts = {};
  let currentView = "30day";

  async function loadTrends(view) {
    const response = await fetch(`/api/trends?view=${view}`, { headers: { Accept: "application/json" } });
    if (!response.ok) {
      console.error("Failed to load trend data", response.status);
      return;
    }
    const data = await response.json();
    updateSubtitle(view, data);

    const showEmpty = view === "since_addition" && !data.has_last_addition;
    document.getElementById("since-addition-empty").hidden = !showEmpty;
    document.querySelector(".chart-grid").hidden = showEmpty;
    if (showEmpty) return;

    renderCharts(data);
  }

  function formatTimestamp(iso) {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function updateSubtitle(view, data) {
    const subtitle = document.getElementById("view-subtitle");
    if (view === "30day") {
      const additionText = data.last_addition_at
        ? `Chemicals last added ${formatTimestamp(data.last_addition_at)}.`
        : "No chemical additions logged yet.";
      subtitle.textContent = `Trends over the last ${data.window_days} days. ${additionText}`;
    } else {
      subtitle.textContent = data.has_last_addition
        ? `Levels since chemicals were last added on ${formatTimestamp(data.last_addition_at)}.`
        : "No chemical additions logged yet.";
    }
  }

  function additionAnnotations(data) {
    return data.additions.map((addition) => ({
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
  }

  function renderCharts(data) {
    const additionLines = additionAnnotations(data);

    document.querySelectorAll("canvas[data-field]").forEach((canvas) => {
      const field = canvas.dataset.field;
      const points = data.readings
        .filter((r) => r[field] !== null && r[field] !== undefined)
        .map((r) => ({ x: r.timestamp, y: r[field] }));

      const existing = charts[field];
      if (existing) {
        existing.data.datasets[0].data = points;
        existing.options.plugins.annotation.annotations = additionLines;
        existing.update();
        return;
      }

      charts[field] = new Chart(canvas, {
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

  document.querySelectorAll(".view-toggle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.view === currentView) return;
      currentView = btn.dataset.view;
      document.querySelectorAll(".view-toggle-btn").forEach((b) => {
        const active = b === btn;
        b.classList.toggle("btn-primary", active);
        b.classList.toggle("btn-secondary", !active);
      });
      loadTrends(currentView);
    });
  });

  loadTrends(currentView);
})();
