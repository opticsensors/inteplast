/* Evolución de una cota: líneas por cavidad, tramos entre muestreos y panel del tramo, como en la app principal.
   Es un SVG propio porque los tramos tienen que poder pulsarse. Usa esc, h, num, una, api y tooltip de app.js. */
"use strict"

const PALETA = ["#2563eb", "#8b5cf6", "#d97706", "#0891b2", "#db2777", "#16a34a", "#dc2626", "#64748b"]
const MAX_CAVIDADES_VISIBLES = 8
const HOJA_CSV = "CSV de la CMM"
const fmt = (v) => Number(v).toLocaleString("es-ES", { maximumFractionDigits: 4 })
const muestreos = (n) => (n === 1 ? "1 muestreo" : `${n} muestreos`)
const cuantasCorrecciones = (n) => (n === 1 ? "1 corrección" : `${n} correcciones`)
const colorCavidad = (r, c) => PALETA[r.cavidades.indexOf(c) % PALETA.length]

function datosGrafica(r, visibles) {
  return {
    etiquetas: r.muestreos.map((m) => m.etiqueta), series: r.muestreos.map((m) => m.serie), banda: r.banda,
    lineas: visibles.map((c) => ({ nombre: c, color: colorCavidad(r, c), puntos: r.puntos[c] })),
  }
}

// Lleno: medido en la pestaña elegida. Hueco: de otra pestaña. Rombo: mismos valores que un muestreo anterior.
function marcaPunto(p, x, y, color) {
  const borde = `fill="${p.hueco ? "var(--panel)" : color}" stroke="${color}" stroke-width="2"`
  return p.repite
    ? `<rect x="${x - 4.2}" y="${y - 4.2}" width="8.4" height="8.4" transform="rotate(45 ${x} ${y})" ${borde}/>`
    : `<circle cx="${x}" cy="${y}" r="4" ${borde}/>`
}

function detallePunto(p, nombre, color) {
  const fichero = `${esc(p.carpeta)}/${esc(p.fichero)}`
  const origen = p.hoja === HOJA_CSV
    ? `${fichero}, ${esc(p.celda)}`
    : `${fichero}<br>${esc(p.hoja)}!${esc(p.celda)}${p.csv ? `<br>CSV: ${esc(p.csv.carpeta)}/${esc(p.csv.fichero)}, línea ${p.csv.linea}${p.csv.columna ? `, columna ${esc(p.csv.columna)}` : ""}` : ""}`
  return `<div class="tip-punto"><span class="punto" style="background:${color}"></span><b>${esc(nombre.toUpperCase())}: ${fmt(p.v)}${p.media ? " (media)" : ""}</b>
    <div class="tip-origen">${origen}${p.fecha ? `<br>Fecha del informe: ${esc(p.fecha)}` : ""}</div>
    ${p.avisos.map((a) => `<div class="tip-aviso">${esc(a)}</div>`).join("")}
    ${(p.info || []).map((a) => `<div class="tip-info">${esc(a)}</div>`).join("")}</div>`
}

function graficaLineas(el, g) {
  const alto = g.alto || 300
  const margen = g.margen ?? 64
  let puntos = []
  const pinta = () => {
    const ancho = Math.max(el.clientWidth, 120)
    const n = g.etiquetas.length
    const x = (i) => (n === 1 ? ancho / 2 : margen + i * (ancho - 2 * margen) / (n - 1))
    const valores = g.lineas.flatMap((l) => l.puntos.filter(Boolean).map((p) => p.v))
    const todos = [...valores, ...(g.banda ? [g.banda.inf, g.banda.sup] : [])]
    if (!todos.length) { el.innerHTML = `<div class="vacio">Sin puntos para esta selección.</div>`; puntos = []; return }
    const relleno = Math.max((Math.max(...todos) - Math.min(...todos)) * 0.15, 0.01)
    const min = Math.min(...todos) - relleno, max = Math.max(...todos) + relleno
    const arriba = 16, abajo = alto - 44
    const y = (v) => abajo - (v - min) / (max - min) * (abajo - arriba)
    const izquierda = margen - 10, derecha = ancho - margen + 10
    const paso = n > 1 ? (ancho - 2 * margen) / (n - 1) : 999
    const compacto = paso < 60
    const cadaCuantos = paso < 24 ? Math.ceil(24 / paso) : 1
    let svg = ""
    for (const t of g.tramos || []) {
      const clases = `tramo ${t.id === g.tramoSel ? "sel" : ""}`
      const cuantas = t.correcciones.length
      svg += `<rect class="${clases}" data-tramo="${esc(t.id)}" x="${x(t.de)}" y="${arriba}" width="${x(t.a) - x(t.de)}" height="${abajo - arriba}"><title>${esc(g.etiquetas[t.de])} a ${esc(g.etiquetas[t.a])}${cuantas ? ` · ${cuantas} corrección(es)` : ""}</title></rect>`
      if (cuantas) svg += `<circle class="marca-tramo" cx="${(x(t.de) + x(t.a)) / 2}" cy="${arriba + 7}" r="3.5"/>`
    }
    if (g.banda) {
      svg += `<rect class="banda" x="${izquierda}" y="${y(g.banda.sup)}" width="${derecha - izquierda}" height="${Math.max(1, y(g.banda.inf) - y(g.banda.sup))}"/>`
      for (const v of [g.banda.inf, g.banda.sup]) {
        svg += `<line class="limite" x1="${izquierda}" x2="${derecha}" y1="${y(v)}" y2="${y(v)}"/>`
        if (margen > 40) svg += `<text class="limite-texto" x="${derecha + 4}" y="${y(v) + 4}">${fmt(v)}</text>`
      }
    }
    for (const v of [min, (min + max) / 2, max]) {
      svg += `<line class="rejilla-linea" x1="${izquierda}" x2="${derecha}" y1="${y(v)}" y2="${y(v)}"/><text class="eje" x="${izquierda - 4}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`
    }
    for (const l of g.lineas) {
      l.puntos.forEach((p, i) => {
        const previo = l.puntos[i - 1]
        if (p && previo && g.series[i] === g.series[i - 1]) {
          svg += `<line x1="${x(i - 1)}" y1="${y(previo.v)}" x2="${x(i)}" y2="${y(p.v)}" stroke="${l.color}" stroke-width="2" ${p.hueco || previo.hueco ? 'stroke-dasharray="5 4"' : ""}/>`
        }
      })
    }
    puntos = []
    for (const l of g.lineas) {
      l.puntos.forEach((p, i) => {
        if (!p) return
        svg += marcaPunto(p, x(i), y(p.v), l.color)
        puntos.push({ p, i, x: x(i), y: y(p.v), nombre: l.nombre, color: l.color })
      })
    }
    g.etiquetas.forEach((e, i) => {
      if (i % cadaCuantos === 0) svg += `<text class="eje" x="${x(i)}" y="${abajo + 18}" text-anchor="middle">${esc(compacto ? e.replace(/^intern\./, "") : e)}</text>`
    })
    if (compacto && margen > 50) svg += `<text class="eje" x="${izquierda - 4}" y="${abajo + 18}" text-anchor="end">intern.</text>`
    el.innerHTML = `<svg class="grafica-lineas" viewBox="0 0 ${ancho} ${alto}" style="height:${alto}px" role="img">${svg}</svg>`
    el.querySelectorAll("[data-tramo]").forEach((r) => { r.onclick = () => g.alPulsarTramo?.(r.dataset.tramo) })
  }
  pinta()
  // Los puntos no reciben el ratón: así el tramo de debajo se puede pulsar aunque el puntero esté sobre una línea.
  el.onmousemove = (e) => {
    const caja = el.getBoundingClientRect()
    let cerca = null, mejor = 9
    for (const q of puntos) {
      const d = Math.hypot(q.x - (e.clientX - caja.left), q.y - (e.clientY - caja.top))
      if (d < mejor) { mejor = d; cerca = q }
    }
    if (!cerca) { tooltip.style.display = "none"; return }
    const juntos = puntos.filter((q) => q.i === cerca.i && Math.hypot(q.x - cerca.x, q.y - cerca.y) <= 4)
    tooltip.innerHTML = `<b>${esc(g.etiquetas[cerca.i])}</b>${juntos.map((q) => detallePunto(q.p, q.nombre, q.color)).join("")}`
    tooltip.style.display = "block"
    tooltip.style.left = `${Math.min(e.clientX + 14, innerWidth - tooltip.offsetWidth - 8)}px`
    tooltip.style.top = `${Math.max(8, Math.min(e.clientY + 14, innerHeight - tooltip.offsetHeight - 8))}px`
  }
  el.onmouseleave = () => { tooltip.style.display = "none" }
  const observador = new ResizeObserver(() => { if (el.isConnected) pinta(); else observador.disconnect() })
  observador.observe(el)
}

function tablaExcluidos(r, abierta) {
  if (!r.excluidos.length) return ""
  return `<details class="nota" ${abierta ? "open" : ""}><summary>${r.excluidos.length} valores excluidos${r.elemento ? " de este elemento" : ""}</summary><table><tr><th>Muestreo</th><th>Cavidad</th><th>Valor</th><th>Motivo</th><th>Origen</th></tr>
    ${r.excluidos.map((x) => `<tr><td>${esc(x.muestreo)}</td><td>${esc(x.cavidad)}</td><td>${fmt(x.valor)}</td><td>${esc(x.motivo)}</td><td>${esc(x.carpeta)}/${esc(x.fichero)} · ${esc(x.hoja)}!${esc(x.celda)}</td></tr>`).join("")}</table></details>`
}

function notaSinMuestreo(r) {
  return r.info.sin_muestreo ? `<div class="nota">${num(r.info.sin_muestreo)} valores más están en ficheros sin <code>intern.NN</code> (entregas PPAP, estudios): no entran en la línea.</div>` : ""
}

/* Devuelve la función que muestra una cota: componente, pestaña, elemento, cavidades, tramos y panel.
   `alCargar` recibe cada respuesta, para que la cabecera de la ficha diga lo mismo que la gráfica. */
function evolucionCota(contenedor, codigo, { componente = null, alCargar = null } = {}) {
  const estado = { cota: null, componente, hoja: null, elemento: null, visibles: null, correcciones: false, tramo: null, r: null }
  const reinicio = { hoja: null, elemento: null, visibles: null, tramo: null }

  const pinta = () => {
    const r = estado.r
    const selectorComponente = r.componentes.length
      ? `<label>Componente <select id="selComponente">${r.componentes.map((x) => `<option value="${esc(x.id)}" ${x.id === r.componente ? "selected" : ""}>${esc(x.etiqueta)}</option>`).join("")}</select></label>`
      : ""
    const enganchaComponente = () => {
      const sel = document.getElementById("selComponente")
      if (sel) sel.onchange = (e) => carga({ ...reinicio, componente: e.target.value })
    }
    if (!r.elemento) {
      const etiqueta = r.componentes.find((x) => x.id === r.componente)?.etiqueta
      contenedor.innerHTML = `${selectorComponente ? `<div class="selectores">${selectorComponente}</div>` : ""}
        ${r.excluidos.length
          ? `<div class="alerta">Todos los valores de esta cota${etiqueta ? ` en ${esc(etiqueta)}` : ""} están excluidos: no hay ninguno que dibujar.</div>${tablaExcluidos(r, true)}`
          : `<div class="vacio">Sin medidas con muestreo identificable para esta cota${etiqueta ? ` en ${esc(etiqueta)}` : ""}.</div>`}
        ${notaSinMuestreo(r)}`
      enganchaComponente()
      return
    }
    const seleccion = estado.visibles.filter((c) => r.cavidades.includes(c))
    // Por defecto, el tramo donde se valida una corrección: ahí se ve su efecto.
    const seValida = (t) => t.correcciones.some((i) => r.correcciones[i].validacion === r.muestreos[t.a].n)
    const tramo = r.tramos.find((t) => t.id === estado.tramo) || r.tramos.find(seValida) || r.tramos.find((t) => t.correcciones.length) || r.tramos[0]
    estado.tramo = tramo?.id
    const res = r.resumen
    const cifras = [
      `${num(res.puntos)} puntos`,
      res.huecos && `${num(res.huecos)} de otra pestaña`,
      res.repetidos && `${num(res.repetidos)} con los mismos valores que un muestreo anterior`,
      res.otro_valor && `${num(res.otro_valor)} con otro valor (al pasar el ratón)`,
      res.medias && `${num(res.medias)} son media de varias piezas`,
      res.csv && `${num(res.csv)} con CSV de la CMM`,
    ].filter(Boolean).join(" · ")
    contenedor.innerHTML = `
      <div class="selectores">
        ${selectorComponente}
        <label>Pestaña <select id="selHoja">${r.hojas.map((x) => `<option value="${esc(x.hoja)}" ${x.hoja === r.hoja ? "selected" : ""}>${esc(x.hoja)} · ${muestreos(x.muestreos)}</option>`).join("")}</select></label>
        <label>Elemento <select id="selElemento">${r.elementos.map((x) => `<option value="${esc(x.id)}" ${x.id === r.elemento ? "selected" : ""}>${esc(x.etiqueta)} · ${muestreos(x.muestreos)}</option>`).join("")}</select></label>
        <button id="btnCorrecciones" aria-pressed="${estado.correcciones}" class="${estado.correcciones ? "activo" : ""}" ${r.tramos.length ? "" : "disabled"}>Correcciones</button>
      </div>
      <div class="nota">${esc(cifras)}</div>
      <div id="grafica"></div>
      <div class="cavidades" id="cavidades"></div>
      <div class="nota">Punto lleno: medido en esa pestaña. Hueco y línea discontinua: de otra pestaña del mismo informe. Rombo: mismos valores que un muestreo anterior; no se da por erróneo.${r.banda ? " Banda verde: tolerancia." : ""}${estado.correcciones ? " Pulsa un tramo; los del punto naranja tienen correcciones." : ""}</div>
      ${r.tolerancia_cambia ? `<div class="alerta">La tolerancia de este elemento cambia entre informes: no se dibuja la banda.</div>` : ""}
      ${r.sin_elemento.length ? `<div class="nota">Esta cota también está en ${r.sin_elemento.map(esc).join(", ")}, pero sin este elemento en ninguna pestaña.</div>` : ""}
      ${notaSinMuestreo(r)}
      ${tablaExcluidos(r, false)}
      <div id="panelTramo"></div>`
    enganchaComponente()
    const cavidades = document.getElementById("cavidades")
    for (const c of r.cavidades) {
      const activa = seleccion.includes(c)
      const b = h(`<button class="${activa ? "" : "apagada"}" aria-pressed="${activa}"><span class="punto" style="background:${colorCavidad(r, c)}"></span>${esc(c.toUpperCase())}</button>`)
      b.onclick = () => {
        if (activa && seleccion.length === 1) return
        estado.visibles = activa ? seleccion.filter((x) => x !== c) : [...seleccion, c]
        pinta()
      }
      cavidades.append(b)
    }
    if (r.cavidades.length > MAX_CAVIDADES_VISIBLES) {
      const todas = h(`<button>Todas</button>`)
      todas.onclick = () => { estado.visibles = [...r.cavidades]; pinta() }
      const pocas = h(`<button>Primeras ${MAX_CAVIDADES_VISIBLES}</button>`)
      pocas.onclick = () => { estado.visibles = r.cavidades.slice(0, MAX_CAVIDADES_VISIBLES); pinta() }
      cavidades.append(todas, pocas)
    }
    graficaLineas(document.getElementById("grafica"), {
      ...datosGrafica(r, seleccion), alto: 340,
      tramos: estado.correcciones ? r.tramos : null, tramoSel: estado.tramo,
      alPulsarTramo: (id) => { estado.tramo = id; pinta() },
    })
    if (estado.correcciones && tramo) panelTramo(document.getElementById("panelTramo"), r, tramo, seleccion)
    document.getElementById("selHoja").onchange = (e) => carga({ hoja: e.target.value })
    document.getElementById("selElemento").onchange = (e) => carga({ elemento: e.target.value })
    document.getElementById("btnCorrecciones").onclick = () => { estado.correcciones = !estado.correcciones; pinta() }
  }

  let ultimoPedido = 0
  const carga = async (cambio) => {
    Object.assign(estado, cambio)
    const p = new URLSearchParams({ c: estado.cota })
    if (estado.componente) p.set("componente", estado.componente)
    if (estado.hoja) p.set("hoja", estado.hoja)
    if (estado.elemento) p.set("elemento", estado.elemento)
    const pedido = ++ultimoPedido
    contenedor.classList.add("cargando")
    let r
    try {
      r = await una(`/api/pieza/${codigo}/cota?${p}`)
    } catch (e) {
      if (pedido === ultimoPedido) contenedor.innerHTML = `<div class="vacio">No se ha podido leer la cota: ${esc(e.message)}</div>`
      return
    } finally {
      if (pedido === ultimoPedido) contenedor.classList.remove("cargando")
    }
    if (pedido !== ultimoPedido || !contenedor.isConnected) return // ya se ha pedido otra cosa
    estado.r = r
    estado.componente = r.componente
    estado.hoja = r.hoja
    estado.elemento = r.elemento
    if (!estado.visibles?.some((c) => r.cavidades.includes(c))) estado.visibles = r.cavidades.slice(0, MAX_CAVIDADES_VISIBLES)
    alCargar?.(r)
    pinta()
  }

  return (cota) => (cota === estado.cota ? null : carga({ ...reinicio, cota }))
}

function nombreCorreccion(x) {
  return x.numero ? `Corrección ${esc(x.numero)}` : "Corrección sin número"
}

/* Todas las variantes a la vista, cada una con su fichero y diapositiva. La preferente solo sale de lo documentado. */
function htmlCorreccion(x) {
  const muestreo = (n) => (n != null ? `intern.${String(n).padStart(2, "0")}` : "sin identificar")
  const varias = x.variantes.length > 1
  const hayPreferente = x.variantes.some((v) => v.preferente)
  return `<div class="correccion">
    <h4>Cambio propuesto en el molde · ${nombreCorreccion(x)}</h4>
    ${x.textos_distintos && !hayPreferente ? `<div class="alerta">Hay ${x.variantes.length} variantes con texto distinto y no consta cuál vale.</div>` : ""}
    ${x.variantes.map((v, i) => `<div class="${varias ? "variante" : ""}">
      ${varias ? `<span class="chip ${v.preferente ? "verde" : ""}">${v.preferente ? "Versión indicada en la ficha de la pieza" : `Variante ${i + 1}`}</span>` : ""}
      ${v.texto.length ? v.texto.map((p) => `<p>${esc(p)}</p>`).join("") : `<p class="nota">La diapositiva no tiene texto propio: la propuesta está en sus imágenes, que aún no se muestran.</p>`}
      <div class="nota">${v.copias.map((c) => `<code>${esc(c.carpeta)}/${esc(c.pptx)}</code>, diapositiva ${c.diapositiva}`).join(" · ")}</div>
      ${v.estado ? `<div class="nota">Validación: ${esc(v.estado)}.</div>` : ""}
      ${v.avisos.length ? `<details class="nota"><summary>${v.avisos.length} aviso(s) de la cadena de correcciones</summary>${v.avisos.map((a) => `<div>${esc(a)}</div>`).join("")}</details>` : ""}
    </div>`).join("")}
    <div class="nota">Origen ${muestreo(x.origen)} · validación ${muestreo(x.validacion)}. Ejecución no confirmada en los documentos.</div>
  </div>`
}

function panelTramo(el, r, t, visibles) {
  const a = r.muestreos[t.de], b = r.muestreos[t.a]
  const lista = t.correcciones.map((i) => r.correcciones[i])
  const titulo = lista.length ? [...new Set(lista.map((x) => `${nombreCorreccion(x)}${x.fecha ? ` · ${esc(x.fecha)}` : ""}`))].join(" / ") : "Seguimiento posterior"
  const dos = (c) => [r.puntos[c][t.de], r.puntos[c][t.a]]
  const filas = visibles.map((c) => {
    const [pa, pb] = dos(c)
    const cambio = pa && pb ? +(pb.v - pa.v).toFixed(4) : null
    return `<tr><td><span class="punto" style="background:${colorCavidad(r, c)}"></span>${esc(c.toUpperCase())}</td><td>${pa ? fmt(pa.v) : "—"}</td><td>${pb ? fmt(pb.v) : "—"}</td><td><b>${cambio == null ? "—" : `${cambio > 0 ? "+" : ""}${fmt(cambio)}`}</b></td></tr>`
  }).join("")
  const repite = [...new Set(visibles.flatMap((c) => dos(c).filter((p) => p?.repite).map((p) => p.repite)))]
  el.innerHTML = `<section class="panel-tramo" aria-label="Detalle del tramo">
      <div class="panel-cabecera"><h3>${titulo}</h3><span class="nota">${esc(a.etiqueta)} a ${esc(b.etiqueta)}</span></div>
      <div class="panel-cuerpo"><div id="graficaTramo"></div>
        <table class="cambios"><tr><th>Cavidad</th><th>${esc(a.etiqueta)}</th><th>${esc(b.etiqueta)}</th><th>Cambio</th></tr>${filas}</table></div>
      ${repite.length ? `<div class="alerta">Algún punto de este tramo tiene los mismos valores que ${repite.map(esc).join(", ")}: el cambio puede no ser una medida nueva.</div>` : ""}
      ${lista.length ? lista.map(htmlCorreccion).join("") : `<p class="nota">No hay ninguna corrección de esta cota enlazada a este tramo. Una diferencia entre medidas no implica un retoque.</p>`}
      ${r.correcciones_sin_tramo ? `<p class="nota">${r.correcciones_sin_tramo} corrección(es) de esta cota no encajan en ningún tramo: están en la tabla de abajo.</p>` : ""}
    </section>`
  graficaLineas(document.getElementById("graficaTramo"), {
    etiquetas: [a.etiqueta, b.etiqueta], series: [a.serie, b.serie], banda: r.banda, alto: 240, margen: 66,
    lineas: visibles.map((c) => ({ nombre: c, color: colorCavidad(r, c), puntos: dos(c) })),
  })
}
