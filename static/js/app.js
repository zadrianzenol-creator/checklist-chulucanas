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
    slug(estado) {
      return estado.toLowerCase().replace(/ó/g, "o").replace(/á/g, "a").replace(/\s+/g, "-");
    },
    helperRecarga() {
      // Las vistas por bandejas/lotes reorganizan grupos; recarga limpia
      const p = location.pathname;
      return p.includes("/bandeja") || p.includes("/recepcion") || p.includes("/lotes");
    },
    async postJSON(url, body = {}) {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "No se pudo completar la operación.");
      return data;
    },
    async transicionar(mesaId, estado, observacion = "") {
      if (this.helperRecarga()) {
        await this.postJSON(`/api/mesas/${mesaId}/transicion`, { estado, observacion });
        this.toast(`Mesa actualizada correctamente`);
        setTimeout(() => location.reload(), 600);
        return;
      }
      try {
        const data = await this.postJSON(`/api/mesas/${mesaId}/transicion`, { estado, observacion });
        const card = $(`[data-mesa-card][data-mesa-id="${mesaId}"]`);
        if (card) {
          card.dataset.estado = estado;
          const chip = card.querySelector("[data-chip]");
          if (chip) chip.className = `st-chip st-${this.slug(estado)}`;
          const acc = card.querySelector("[data-mesa-acciones]");
          if (acc) acc.classList.add("done");
        }
        if (estado === "OBSERVADA") {
          const ot = card ? card.querySelector("[data-obs-text]") : null;
          if (ot) ot.textContent = "Observación: " + observacion;
        }
        this.toast(`Mesa ${data.mesa ? "→ " + estado : ""}`);
        setTimeout(() => location.reload(), 900);
      } catch (err) {
        this.toast(err.message, "error");
      }
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
        if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && !burger.contains(e.target)) {
          sidebar.classList.remove("open");
        }
      });
    }

    // ---------- Modales ----------
    $$("[data-open-modal]").forEach((btn) => btn.addEventListener("click", () => App.openModal(btn.dataset.openModal)));
    $$("[data-close-modal]").forEach((btn) => btn.addEventListener("click", () => App.closeModal(btn.dataset.closeModal)));
    $$(".modal-overlay").forEach((ov) => {
      ov.addEventListener("click", (e) => {
        if (e.target === ov) ov.classList.remove("open");
      });
    });

    // ---------- Tilt 3D ----------
    if (window.matchMedia("(min-width: 961px)").matches && navigator.maxTouchPoints === 0) {
      $$(".tilt").forEach((card) => {
        card.addEventListener("pointermove", (e) => {
          const r = card.getBoundingClientRect();
          const px = (e.clientX - r.left) / r.width - 0.5;
          const py = (e.clientY - r.top) / r.height - 0.5;
          card.style.transform = `perspective(900px) rotateX(${-py * 7}deg) rotateY(${px * 9}deg) translateY(-2px)`;
        });
        card.addEventListener("pointerleave", () => (card.style.transform = ""));
      });
    }

    // ---------- Filtros de grillas ----------
    $$("[data-filter-group]").forEach((group) => {
      const seg = group.querySelector("[data-filter-seg]");
      const cards = group.querySelectorAll("[data-mesa-card]");
      const apply = () => {
        const value = seg ? seg.dataset.filterValue : "all";
        const q = (group.dataset.searchValue || "").toLowerCase();
        cards.forEach((c) => {
          const est = (c.dataset.estado || "PENDIENTE").toUpperCase();
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

    // ---------- Búsqueda simple en tablas ----------
    $$("[data-search-group]").forEach((group) => {
      const input = group.querySelector("[data-search-input]");
      if (!input) return;
      input.addEventListener("input", () => {
        const q = input.value.toLowerCase();
        $$("[data-row-search]", group).forEach((row) => {
          row.classList.toggle("is-hidden", !(row.dataset.searchText || "").toLowerCase().includes(q));
        });
      });
    });

    // ---------- Transiciones de estado ----------
    $$("[data-trans]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const mesaId = btn.dataset.trans;
        const estado = btn.dataset.estado;
        if (!mesaId || !estado) return;
        if (btn.disabled) return;
        btn.disabled = true;
        App.transicionar(mesaId, estado);
      });
    });

    // ---------- Observar mesa ----------
    const obsModal = $("#modal-observar");
    const abrirObservar = (mesaId, nombre) => {
      if (!obsModal) return;
      obsModal.dataset.mesaId = mesaId;
      const n = obsModal.querySelector("[data-obs-nombre]");
      if (n) n.textContent = nombre || `Mesa ${mesaId}`;
      const ta = obsModal.querySelector("textarea");
      if (ta) ta.value = "";
      App.openModal("modal-observar");
      setTimeout(() => { if (ta) ta.focus(); }, 80);
    };
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-observar]");
      if (btn) {
        const card = btn.closest("[data-mesa-card]");
        abrirObservar(btn.dataset.observar, card ? card.dataset.mesaLabel : "");
      }
    });
    const obsBtn = $("#btn-observar-confirmar");
    if (obsBtn && obsModal) {
      obsBtn.addEventListener("click", async () => {
        const mesaId = obsModal.dataset.mesaId;
        const ta = obsModal.querySelector("textarea");
        const text = (ta && ta.value || "").trim();
        App.closeModal("modal-observar");
        await App.transicionar(mesaId, "OBSERVADA", text);
      });
    }

    // ---------- Asignación de mesas (admin) ----------
    $$("[data-asignar-select]").forEach((sel) => {
      let antes = sel.value;
      sel.addEventListener("change", async () => {
        const mesaId = sel.dataset.asignarSelect;
        const digId = sel.value || null;
        try {
          const data = await App.postJSON(`/api/mesas/${mesaId}/asignar`, { digitador_id: digId });
          antes = sel.value;
          App.toast(data.digitador ? `Mesa asignada a ${data.digitador}` : "Mesa sin digitador");
        } catch (err) {
          sel.value = antes;
          App.toast(err.message, "error");
        }
      });
    });

    // Asignación masiva
    const asignarBar = $("[data-asignar-bar]");
    if (asignarBar) {
      const dig = asignarBar.querySelector("#asignar-dig");
      const btn = asignarBar.querySelector("[data-asignar-bulk]");
      const refresh = () => {
        if (btn) btn.disabled = $$("[data-asignar-pick]:checked").length === 0;
      };
      $$("[data-asignar-pick]").forEach((cb) => cb.addEventListener("change", refresh));
      if (btn) {
        btn.addEventListener("click", async () => {
          const ids = $$("[data-asignar-pick]:checked").map((cb) => cb.dataset.asignarPick);
          if (!ids.length) return App.toast("Selecciona al menos una mesa.", "error");
          if (!dig.value) return App.toast("Elige un digitador para asignar.", "error");
          btn.disabled = true;
          let ok = 0;
          try {
            for (const id of ids) {
              await App.postJSON(`/api/mesas/${id}/asignar`, { digitador_id: dig.value });
              ok++;
            }
            App.toast(`${ok} mesa(s) asignada(s)`);
            setTimeout(() => location.reload(), 700);
          } catch (err) {
            App.toast(err.message, "error");
          } finally {
            btn.disabled = false;
          }
        });
      }
    }

    // ---------- Recepción: acciones masivas ----------
    $$("[data-accion-bulk]").forEach((btn) => {
      const grupo = btn.closest("[data-select-group]") || document;
      const tipo = btn.dataset.tipo;
      const refresh = () => {
        const n = $$(`.ck[data-pick="${tipo}"]:checked`, grupo).length;
        btn.disabled = n === 0;
      };
      $$(`.ck[data-pick="${tipo}"]`, grupo).forEach((cb) => cb.addEventListener("change", refresh));
      refresh();

      btn.addEventListener("click", async () => {
        const ids = $$(`.ck[data-pick="${tipo}"]:checked`, grupo).map((cb) => cb.dataset.mesaId);
        if (!ids.length) return;
        btn.disabled = true;
        try {
          if (tipo === "lote") {
            const data = await App.postJSON("/api/lotes/crear", { mesa_ids: ids });
            App.toast(`${data.lote.codigo} creado con ${ids.length} mesas`);
          } else if (tipo === "llegada") {
            for (const id of ids) await App.postJSON(`/api/mesas/${id}/llegada`);
            App.toast(`${ids.length} acta(s) en pendiente de control`);
          } else if (tipo === "archivo") {
            for (const id of ids) await App.postJSON(`/api/mesas/${id}/archivar`);
            App.toast(`${ids.length} mesa(s) archivadas y cerradas`);
          }
          setTimeout(() => location.reload(), 600);
        } catch (err) {
          App.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    });

    // ---------- Lotes: entregar / recibir / archivar ----------
    $$("[data-entregar-lote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.entregarLote;
        const sel = btn.closest("[data-lote]") ? btn.closest("[data-lote]").querySelector("[data-lote-dig]") : $("#lote-dig");
        const digId = sel ? sel.value : "";
        if (!digId) return App.toast("Elige un digitador para el lote.", "error");
        btn.disabled = true;
        try {
          const data = await App.postJSON(`/api/lotes/${id}/entregar`, { digitador_id: digId });
          App.toast(`${data.lote.codigo} entregado para control de calidad`);
          setTimeout(() => location.reload(), 600);
        } catch (err) {
          App.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    });
    $$("[data-recibir-lote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.recibirLote;
        btn.disabled = true;
        try {
          await App.postJSON(`/api/lotes/${id}/recibir`);
          App.toast("Lote devuelto a custodia");
          setTimeout(() => location.reload(), 600);
        } catch (err) {
          App.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    });
    $$("[data-archivar-lote]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.archivarLote;
        btn.disabled = true;
        try {
          const data = await App.postJSON(`/api/lotes/${id}/archivar`);
          App.toast(`${data.cuenta} mesa(s) archivadas del lote`);
          setTimeout(() => location.reload(), 600);
        } catch (err) {
          App.toast(err.message, "error");
          btn.disabled = false;
        }
      });
    });
    $$("[data-ver-lote]").forEach((btn) => {
      btn.addEventListener("click", () => {
        location.href = `/lotes/${btn.dataset.verLote}`;
      });
    });

    // ---------- Trazabilidad ----------
    const trazaModal = $("#modal-traza");
    const abrirTraza = async (mesaId, nombre) => {
      if (!trazaModal) return;
      const nom = trazaModal.querySelector("[data-traza-nombre]");
      if (nom) nom.textContent = nombre || `Mesa ${mesaId}`;
      const ev = trazaModal.querySelector("[data-traza-eventos]");
      const obs = trazaModal.querySelector("#obs-historial");
      if (ev) ev.innerHTML = '<div class="t-line-loading">Cargando historial…</div>';
      if (obs) obs.innerHTML = "";
      App.openModal("modal-traza");
      try {
        const res = await fetch(`/api/mesas/${mesaId}/trazabilidad`);
        const data = await res.json();
        if (!data.ok) throw new Error("Error al leer la trazabilidad");
        if (ev) {
          ev.innerHTML = data.eventos.length
            ? data.eventos.map((e) => `
                <div class="tl-item">
                  <i class="tl-dot"></i>
                  <div class="tl-body">
                    <p>${e.detalle}</p>
                    <span>${e.usuario} · ${App.formatoFecha(e.fecha)}</span>
                  </div>
                </div>`).join("")
            : '<div class="tl-empty">Sin movimientos registrados.</div>';
        }
        if (obs) {
          obs.innerHTML = data.observaciones.length
            ? data.observaciones.map((o) => `
                <div class="obs-card ${o.resuelta ? "resuelta" : ""}">
                  <div class="obs-card__head">
                    <span class="badge ${o.resuelta ? "badge-on" : "badge-danger"}">${o.resuelta ? "Resuelta" : "Pendiente"}</span>
                    <span class="muted mono" style="font-size:11px;">${o.autor || "—"} · ${App.formatoFecha(o.fecha)}</span>
                  </div>
                  <p>${o.detalle}</p>
                </div>`).join("")
            : '<div class="tl-empty">Sin observaciones.</div>';
        }
      } catch (err) {
        if (ev) ev.innerHTML = "";
        App.toast(err.message, "error");
      }
    };
    document.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-ver-traza]");
      if (!btn) return;
      const card = btn.closest("[data-mesa-card]");
      abrirTraza(btn.dataset.verTraza, card ? card.dataset.mesaLabel : "");
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
      }
      const num = ring.querySelector("[data-ring-num]");
      if (num) num.textContent = val + "%";
    });
  });

  window.ListApp.formatoFecha = (iso) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString("es-PE", {
      day: "2-digit", month: "2-digit", year: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  };
})();