(() => {
  const selProducto = document.getElementById("producto_id");
  const inpCantidad = document.getElementById("cantidad");
  const btnAgregar = document.getElementById("btnAgregarItem");
  const tbody = document.getElementById("posTbody");
  const totalEl = document.getElementById("posTotal");
  const hidden = document.getElementById("posItemsJson");
  const form = document.getElementById("posForm");
  const ctReg = document.getElementById("ct_reg");
  const ctMos = document.getElementById("ct_mos");
  const bloqueReg = document.querySelector(".pos-bloque-reg");
  const bloqueMos = document.querySelector(".pos-bloque-mos");
  const clienteId = document.getElementById("cliente_id");

  if (!selProducto || !inpCantidad || !btnAgregar || !tbody || !totalEl || !hidden || !form) return;

  /** @type {{producto_id:number,nombre:string,precio:string,cantidad:number,subtotal:string}[]} */
  let items = [];

  /** Precio desde data-precio: preferir valor sin localizar del servidor (ej. 2214000.00). */
  const parsePrecioPos = (raw) => {
    const s = String(raw ?? "").trim();
    if (!s) return 0;
    if (/^\d+(\.\d+)?$/.test(s)) return parseFloat(s);
    const sinMiles = s.replace(/\./g, "").replace(/\s/g, "");
    const comaDecimal = sinMiles.replace(",", ".");
    const n = parseFloat(comaDecimal);
    return Number.isFinite(n) ? n : 0;
  };

  const money = (n) => {
    const num = Number(n || 0);
    return "$" + Math.round(num).toLocaleString("es-CO");
  };

  const syncHidden = () => {
    hidden.value = JSON.stringify(
      items.map((it) => ({
        producto_id: it.producto_id,
        cantidad: it.cantidad,
      }))
    );
  };

  const render = () => {
    if (!items.length) {
      tbody.innerHTML = `<tr class="pos-table__empty"><td colspan="5">Aún no hay productos en esta venta.</td></tr>`;
      totalEl.textContent = "$0";
      syncHidden();
      return;
    }

    tbody.innerHTML = items
      .map((it, idx) => {
        const pu = parsePrecioPos(it.precio);
        const sub = parsePrecioPos(it.subtotal);
        return `
        <tr>
          <td class="pos-table__name">${escapeHtml(it.nombre)}</td>
          <td class="pos-table__num">${it.cantidad}</td>
          <td class="pos-table__num">${money(pu)}</td>
          <td class="pos-table__num pos-table__sub">${money(sub)}</td>
          <td class="pos-table__act">
            <button type="button" data-idx="${idx}" class="pos-btn pos-btn--icon" title="Quitar">
              <i class="bx bx-trash"></i>
            </button>
          </td>
        </tr>
      `;
      })
      .join("");

    const total = items.reduce((acc, it) => acc + parsePrecioPos(it.subtotal), 0);
    totalEl.textContent = money(total);
    syncHidden();
  };

  const escapeHtml = (str) => {
    return String(str || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  };

  const syncModoCliente = () => {
    const mostrador = ctMos && ctMos.checked;
    if (bloqueReg) bloqueReg.style.display = mostrador ? "none" : "block";
    if (bloqueMos) bloqueMos.style.display = mostrador ? "block" : "none";
    if (clienteId) {
      clienteId.required = !mostrador;
      if (mostrador) clienteId.removeAttribute("required");
    }
    const mosIds = ["pv_nombres", "pv_apellidos", "pv_tipo_documento", "pv_numero_documento", "pv_telefono"];
    mosIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (mostrador) el.setAttribute("required", "required");
      else el.removeAttribute("required");
    });
  };

  if (ctReg) ctReg.addEventListener("change", syncModoCliente);
  if (ctMos) ctMos.addEventListener("change", syncModoCliente);
  syncModoCliente();

  btnAgregar.addEventListener("click", () => {
    const opt = selProducto.selectedOptions && selProducto.selectedOptions[0];
    const pid = Number(opt?.value || 0);
    if (!pid) return;

    const stock = Number(opt?.dataset?.stock || 0);
    const nombre = opt?.dataset?.nombre || opt?.textContent || "Producto";
    const precioRaw = opt?.dataset?.precio || "0";
    const precioNum = parsePrecioPos(precioRaw);
    const cant = Math.max(1, Number(inpCantidad.value || 1));

    const existente = items.find((i) => i.producto_id === pid);
    const cantNueva = (existente ? existente.cantidad : 0) + cant;
    if (stock && cantNueva > stock) {
      window.alert("Cantidad supera el stock disponible.");
      return;
    }

    if (existente) {
      existente.cantidad = cantNueva;
      existente.subtotal = String(precioNum * existente.cantidad);
    } else {
      items.push({
        producto_id: pid,
        nombre,
        precio: String(precioNum),
        cantidad: cant,
        subtotal: String(precioNum * cant),
      });
    }
    render();
  });

  tbody.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-idx]");
    if (!btn) return;
    const idx = Number(btn.dataset.idx);
    if (!Number.isFinite(idx)) return;
    items.splice(idx, 1);
    render();
  });

  form.addEventListener("submit", (ev) => {
    if (!items.length) {
      ev.preventDefault();
      window.alert("Agrega al menos un producto.");
      return;
    }
    if (ctReg && ctReg.checked) {
      const v = (clienteId && clienteId.value) || "";
      if (!v) {
        ev.preventDefault();
        window.alert("Selecciona un cliente registrado.");
        return;
      }
    }
    syncHidden();
  });

  render();
})();
