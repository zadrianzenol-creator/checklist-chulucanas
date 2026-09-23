(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  window.ListApp = {
    toast(title, type = "success") {
      const box = $("#toasts");
      if (!box) return;
      const icons = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>',
      };
      const el = document.createElement("div");
      el.className = `toast ${type}`;
      el.innerHTML = `<span class="toast__ic">${icons[type] || icons.success}</span><span>${title}</span>`;
      box.appendChild(el);
      setTimeout(() => {
        el.classList.add("out");
        setTimeout(() => el.remove(), 320);
      }, 3200);
    },
    flashToasts() {
      $$(".flash-zone .toast").forEach((t) => {
        const msg = t.dataset.message || "";
        const type = t.dataset.type === "error" ? "error" : "success";
        this.toast(msg, type);
        t.remove();
      });
    },
    openModal(id) {
      const m = $(`#${id}`);
      if (m) {
        m.classList.add("open");
        const auto = m.querySelector("[data-autofocus]");
        if (auto) setTimeout(() => auto.focus(), 60);
      }
    },
    closeModal(id) {
      const m = $(`#${id}`);
      if (m) m.classList.remove("open");
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    const App = window.ListApp;
    App.flashToasts();

    // ---------- Sidebar móvil ----------
    const burger = $(".burger");
    const sidebar = $(".sidebar");
    if (burger && sidebar) {
      burger.addEventListener("click", () => sidebar.classList.toggle("open"));
      document.addEventListener("click", (e) => {
        if (
          sidebar.classList.contains("open") &&
          !sidebar.contains(e.target) &&
          !burger.contains(e.target)
        ) {
          sidebar.classList.remove("open");
        }
      });
    }

    // ---------- Modales genéricos ----------
    $$("[data-open-modal]").forEach((btn) => {
      btn.addEventListener("click", () => App.openModal(btn.dataset.openModal));
    });
    $$("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => App.closeModal(btn.dataset.closeModal));
    });
    $$(".modal-overlay").forEach((ov) => {
      ov.addEventListener("click", (e) => {
        if (e.target === ov) ov.classList.remove("open");
      });
    });

    // ---------- Efecto 3D tilt en tarjetas ----------
    if (window.matchMedia("(min-width: 961px)").matches) {
      const isCoarse = navigator.maxTouchPoints > 0;
      if (!isCoarse) {
        $$(".tilt").forEach((card) => {
          card.addEventListener("pointermove", (e) => {
            const r = card.getBoundingClientRect();
            const px = (e.clientX - r.left) / r.width - 0.5;
            const py = (e.clientY - r.top) / r.height - 0.5;
            card.style.transform = `perspective(900px) rotateX(${-py * 7}deg) rotateY(${px * 9}deg) translateY(-2px)`;
          });
          card.addEventListener("pointerleave", () => {
            card.style.transform = "";
          });
        });
      }
    }

    // ---------- Filtros de grillas ----------
    $$("[data-filter-group]").forEach((group) => {
      const seg = group.querySelector("[data-filter-seg]");
      const cards = group.querySelectorAll("[data-estado]");

      const apply = () => {
        const value = seg ? seg.dataset.filterValue : "all";
        cards.forEach((c) => {
          const est = (c.dataset.estado || "PENDIENTE").toUpperCase();
          const q = (group.dataset.searchValue || "").toLowerCase();
          const haystack = (c.dataset.searchText || "").toLowerCase();
          const matchEstado = value === "all" || est === value;
          const matchQ = !q || haystack.includes(q);
          c.classList.toggle("is-hidden", !(matchEstado && matchQ));
        });
      };

      if (seg) {
        $$("button", seg).forEach((b) => {
          b.addEventListener("click", () => {
            $$("button", seg).forEach((x) => x.classList.remove("on"));
            b.classList.add("on");
            seg.dataset.filterValue = b.dataset.filter;
            apply();
          });
        });
      }

      if (group.matches("[data-search-group]")) {
        group.addEventListener("input", (e) => {
          if (e.target.matches("[data-search-input]")) {
            group.dataset.searchValue = e.target.value;
            apply();
          }
        });
      }
    });

    // ---------- Marcado de mesas ----------
    $$("[data-mesa-acciones]").forEach((group) => {
      group.addEventListener("click", (e) => {
        const btn = e.target.closest("[data-set-estado]");
        if (!btn) return;
        const mesaId = btn.dataset.mesaId;
        const estado = btn.dataset.setEstado.toUpperCase();
        const card = group.closest("[data-mesa-card]");

        if (estado === "OBSERVADO") {
          const obs = card.querySelector("[data-obs-target]");
          document.dispatchEvent(new CustomEvent("app:observar", { detail: { mesaId, nombre: card.dataset.mesaLabel, obs } }));
          return;
        }
        App.setMesaEstado(mesaId, estado, "");
      });
    });

    App.setMesaEstado = async (mesaId, estado, observacion) => {
      try {
        const res = await fetch(`/api/mesas/${mesaId}/estado`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ estado, observacion }),
        });
        const data = await res.json();
        if (!data.ok) throw new Error(data.error || "Error al actualizar");

        const card = $(`[data-mesa-card][data-mesa-id="${mesaId}"]`);
        if (card) {
          card.dataset.estado = estado;
          const badge = card.querySelector("[data-estado-badge]");
          if (badge) {
            badge.className = `badge badge-${estado.toLowerCase().replace("ó", "o")}`;
            badge.innerHTML = App.estadoBadgeHtml(estado, data.mesa ? data.mesa.observacion : observacion);
          }
          const obs = card.querySelector("[data-obs-text]");
          if (obs) {
            obs.classList.toggle("hide", estado !== "OBSERVADO" || !(data.mesa ? data.mesa.observacion : observacion));
            obs.textContent = data.mesa && data.mesa.observacion ? `<i class="mb-2"></i>` : "";
          }
          if (estado === "OBSERVADO" && data.mesa && data.mesa.observacion) {
            const ot = card.querySelector("[data-obs-text]");
            ot.innerText = "Observación: " + data.mesa.observacion;
          }
        }
        App.actualizarContadores();
        App.toast(`Mesa ${card ? card.dataset.mesaLabel : mesaId} → ${estado}`, "success");
      } catch (err) {
        App.toast(err.message, "error");
      }
    };

    App.estadoBadgeHtml = (estado) => {
      const icons = {
        VERIFICADA: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M20 6 9 17l-5-5"/></svg>',
        OBSERVADO: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>',
        PENDIENTE: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
      };
      return `${icons[estado] || ""}<span>${estado}</span>`;
    };

    App.actualizarContadores = () => {
      // Consumo desde el DOM por tarjetas de mesa del mismo grupo
      $$("[data-local-stats]").forEach((box) => {
        const scope = box.dataset.localStats;
        const cards = scope === "all"
          ? $$("[data-mesa-card]")
          : $$(`[data-mesa-card][data-local-id="${scope}"]`);
        const count = (est) => cards.filter((c) => (c.dataset.estado || "PENDIENTE").toUpperCase() === est).length;
        const v = box.querySelector("[data-c-verificadas]");
        const o = box.querySelector("[data-c-observado]");
        const p = box.querySelector("[data-c-pendiente]");
        if (v) v.textContent = count("VERIFICADA");
        if (o) o.textContent = count("OBSERVADO");
        if (p) p.textContent = count("PENDIENTE");
        const total = cards.length;
        const av = total ? Math.round((count("VERIFICADA") / total) * 100) : 0;
        const bar = box.querySelector("[data-c-avance] span, [data-c-avance] i");
        const pct = box.querySelector("[data-c-pct], [data-c-avance]");
        if (bar && bar.style) {
          bar.style.width = av + "%";
          const num = box.querySelector("[data-c-pct]");
          if (num) num.textContent = av + "%";
        }
      });
    };

    // ---------- Observar mesa ----------
    const obsModal = $("#modal-observar");
    document.addEventListener("app:observar", (e) => {
      if (!obsModal) return;
      const { mesaId } = e.detail;
      obsModal.dataset.mesaId = mesaId;
      const n = obsModal.querySelector("[data-obs-nombre]");
      if (n) n.textContent = `Mesa ${e.detail.nombre || mesaId}`;
      const ta = obsModal.querySelector("[data-obs-input]");
      if (ta) ta.value = e.detail.obs ? e.detail.obs.textContent.replace("Observación: ", "") : "";
      App.openModal("modal-observar");
    });
    const obsBtn = $("#btn-observar-confirmar");
    if (obsBtn && obsModal) {
      obsBtn.addEventListener("click", () => {
        const mesaId = obsModal.dataset.mesaId;
        const text = ($("[data-obs-input]", obsModal) || {}).value || "";
        App.setMesaEstado(mesaId, "OBSERVADO", text.trim());
        App.closeModal("modal-observar");
      });
    }

    // ---------- Reset contraseña ----------
    $$("[data-reset-user]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.dataset.resetUser;
        const modal = $("#modal-reset");
        if (!modal) return;
        modal.dataset.userId = id;
        const n = modal.querySelector("[data-reset-nombre]");
        if (n) n.textContent = btn.dataset.resetNombre || "";
        App.openModal("modal-reset");
      });
    });
    const resetBtn = $("#btn-reset-confirmar");
    if (resetBtn) {
      resetBtn.addEventListener("click", async () => {
        const modal = $("#modal-reset");
        const id = modal.dataset.userId;
        const pass = ($("[data-reset-input]", modal) || {}).value || "";
        try {
          const res = await fetch(`/usuarios/${id}/reset`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ password: pass }),
          });
          const data = await res.json();
          if (!data.ok) throw new Error(data.error || "No se pudo actualizar");
          App.closeModal("modal-reset");
          App.toast(data.message || "Contraseña actualizada", "success");
          ($("[data-reset-input]", modal) || {}).value = "";
        } catch (err) {
          App.toast(err.message, "error");
        }
      });
    }

    // ---------- Toggle usuarios ----------
    $$("[data-toggle-user]").forEach((sw) => {
      sw.addEventListener("change", async () => {
        const id = sw.dataset.toggleUser;
        const checked = sw.checked;
        try {
          const res = await fetch(`/usuarios/${id}/toggle`, { method: "POST" });
          const data = await res.json();
          if (!data.ok) {
            sw.checked = !checked;
            throw new Error(data.error || "No se pudo cambiar el estado");
          }
          App.toast(data.is_active ? "Usuario activado" : "Usuario desactivado", "success");
          const row = sw.closest("tr");
          if (row) {
            const badge = row.querySelector("[data-estado-badge]");
            if (badge) {
              badge.className = `badge ${data.is_active ? "badge-on" : "badge-off"}`;
              badge.innerHTML = `<span>${data.is_active ? "Activo" : "Inactivo"}</span>`;
            }
          }
        } catch (err) {
          App.toast(err.message, "error");
        }
      });
    });

    // ---------- Ánillos de progreso ----------
    $$("[data-ring]").forEach((ring) => {
      const val = parseFloat(ring.dataset.ring || "0");
      const radius = 46;
      const circ = 2 * Math.PI * radius;
      const bar = ring.querySelector(".ring-bar");
      if (bar) {
        bar.style.strokeDasharray = circ;
        bar.style.strokeDashoffset = circ - (circ * val) / 100;
        setTimeout(() => {
          bar.style.strokeDashoffset = circ - (circ * val) / 100;
        }, 60);
      }
      const num = ring.querySelector("[data-ring-num]");
      if (num) num.textContent = val + "%";
    });

    // ---------- Gráficos ----------
    const donutData = $("#chart-donut-data");
    if (donutData && window.Chart) {
      try {
        const d = JSON.parse(donutData.textContent);
        const ctx = donutData.parentElement.querySelector("canvas");
        const colors = ["#fbbf24", "#34d399", "#f87171"];
        new Chart(ctx, {
          type: "doughnut",
          data: {
            labels: ["Pendientes", "Verificadas", "Observadas"],
            datasets: [{
              data: [d.pendientes, d.verificadas, d.observadas],
              backgroundColor: colors,
              borderWidth: 0,
              hoverOffset: 8,
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "72%",
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: "rgba(15,20,40,.95)",
                borderColor: "rgba(255,255,255,.12)",
                borderWidth: 1,
                padding: 12,
                bodyFont: { family: "Inter" },
                titleFont: { family: "Inter" },
              },
            },
          },
        });
      } catch (e) { /* ignore */ }
    }

    const barData = $("#chart-bar-data");
    if (barData && window.Chart) {
      try {
        const d = JSON.parse(barData.textContent);
        const ctx = barData.parentElement.querySelector("canvas");
        const top = d.slice().sort((a, b) => b.total - a.total).slice(0, 10);
        new Chart(ctx, {
          type: "bar",
          data: {
            labels: top.map((x) => `${x.nombre.slice(0, 16)}${x.nombre.length > 16 ? "…" : ""}`),
            datasets: [
              {
                label: "Verificadas",
                data: top.map((x) => x.verificadas),
                backgroundColor: "#34d399",
                borderRadius: 6,
                stack: "s1",
              },
              {
                label: "Observadas",
                data: top.map((x) => x.observadas),
                backgroundColor: "#f87171",
                borderRadius: 6,
                stack: "s1",
              },
              {
                label: "Pendientes",
                data: top.map((x) => x.pendientes),
                backgroundColor: "#fbbf24",
                borderRadius: 6,
                stack: "s1",
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                grid: { color: "rgba(255,255,255,.04)" },
                ticks: { color: "#94a0c4", font: { family: "Inter", size: 10 } },
              },
              y: {
                grid: { color: "rgba(255,255,255,.04)" },
                ticks: { color: "#94a0c4", font: { family: "Inter", size: 11 } },
              },
            },
            plugins: {
              legend: { labels: { color: "#94a0c4", font: { family: "Inter", size: 12 }, usePointStyle: true, pointStyle: "circle" } },
              tooltip: { backgroundColor: "rgba(15,20,40,.95)", borderWidth: 1, borderColor: "rgba(255,255,255,.12)" },
            },
          },
        });
      } catch (e) { /* ignore */ }
    }

    // Valores iniciales contadores (por si no hay AJAX)
    App.actualizarContadores();
  });
})();