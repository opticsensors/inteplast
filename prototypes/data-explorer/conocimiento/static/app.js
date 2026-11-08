/* Visor de conocimiento: interfaz de una sola página con rutas en el hash. */
"use strict"

const vista = document.getElementById("vista")
const tooltip = document.getElementById("tooltip")
const cache = {}
const api = async (url) => {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}
const una = async (url) => (cache[url] ??= api(url))
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c])
const md = (t) => (window.marked ? marked.parse(t || "") : `<pre>${esc(t)}</pre>`)
const num = (n) => (n ?? 0).toLocaleString("es-ES")
const h = (html) => { const d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstElementChild }

function ruta() {
  const [camino, consulta] = location.hash.replace(/^#\/?/, "").split("?")
  const partes = camino.split("/").map(decodeURIComponent)
  return { partes, q: new URLSearchParams(consulta || "") }
}
function ir(hash) { if (location.hash !== hash) location.hash = hash; else render() }


async function render() {
  const { partes, q } = ruta()
  const tab = partes[0] || "planos"
  document.querySelectorAll("header nav a").forEach((a) => a.classList.toggle("activo", a.dataset.tab === tab))
  tooltip.style.display = "none"
  grafoPiezasVivo?.pauseAnimation()
  try {
    if (tab === "planos" && partes[1]) await vistaPlano(+partes[1], q)
    else if (tab === "planos") await vistaPlanos(q)
    else if (tab === "piezas" && partes[1] && !(partes[1] in SUBPESTANAS)) await vistaPieza(partes[1], q)
    else if (tab === "piezas") await vistaPiezas(partes[1] || "", q)
    else if (tab === "grafo") await vistaGrafo(q)
    else if (tab === "esquema") await vistaEsquema()
    else if (tab === "revision") await vistaRevision()
  } catch (e) {
    vista.innerHTML = `<div class="vacio">Error: ${esc(e.message)}</div>`
    console.error(e)
  }
}

const CASOS_VISIBLES = 25 // en la pestaña Revisión; revision.json los guarda todos

/* ------------------------------------------------------------ planos: cuadrícula */

let ordenPlanos = []
let ultimaRejilla = "#/planos"

// Un solo tag por plano: cómo se puede buscar en él.
const TAGS = {
  icp: { texto: "Con .icp", clase: "azul" },
  globos: { texto: "Globos sin .icp", clase: "verde" },
  numerado: { texto: "Numerado sin globos", clase: "naranja" },
  nada: { texto: "Sin globos ni numeración", clase: "rojo" },
}

// El navegador guarda las imágenes un día: un plano enderezado necesita otra dirección para verse al momento.
const imagenPlano = (p, pagina, tipo) => `/api/plano/${p.id}/${pagina}/${tipo}.jpg${p.giro ? `?giro=${p.giro}` : ""}`

function tagPlano(p) {
  const t = TAGS[p.tag]
  return t ? `<span class="chip ${t.clase}">${t.texto}</span>` : ""
}

async function vistaPlanos(q) {
  ultimaRejilla = location.hash || "#/planos"
  const { planos } = await una("/api/planos")
  const texto = q.get("q") || ""
  const feature = q.get("f") || ""
  const tag = q.get("t") || ""
  const features = [...new Set(planos.map((p) => p.feature))].sort()
  vista.innerHTML = `
    <div class="barra">
      <input type="search" id="q" placeholder="Pieza, nombre, feature…" value="${esc(texto)}" style="width:320px">
      <select id="f"><option value="">Todos los features</option>${features.map((f) => `<option ${f === feature ? "selected" : ""}>${esc(f)}</option>`).join("")}</select>
      <select id="t"><option value="">Todos los tags</option>${Object.entries(TAGS).map(([k, v]) => `<option value="${k}" ${k === tag ? "selected" : ""}>${v.texto} (${planos.filter((p) => p.tag === k).length})</option>`).join("")}</select>
    </div>
    <div class="rejilla" id="rejilla"></div>`
  const t = texto.toLowerCase()
  let lista = planos.filter((p) => (!feature || p.feature === feature) && (!tag || p.tag === tag))
  if (texto) lista = lista.filter((p) => `${p.codigo} ${p.nombre} ${p.feature} ${p.ruta}`.toLowerCase().includes(t))
  ordenPlanos = lista.map((p) => p.id)
  const rejilla = document.getElementById("rejilla")
  if (!lista.length) rejilla.innerHTML = `<div class="vacio">Ningún plano coincide.</div>`
  for (const p of lista) {
    const card = h(`<div class="tarjeta ${p.tag === "nada" ? "sin-busqueda" : ""}" title="${esc(p.ruta)}">
      <div class="mini"><img loading="lazy" alt="" src="${imagenPlano(p, 1, "mini")}"></div>
      <div class="pie"><b>${esc(p.codigo)}</b> · ${esc(p.feature)}
        <div class="nombre">${esc(p.nombre)}</div>
        ${tagPlano(p)}
      </div></div>`)
    const img = card.querySelector("img")
    img.onerror = () => { img.replaceWith(h(`<span>sin imagen (¿en la nube?)</span>`)) }
    card.onclick = () => ir(`#/planos/${p.id}`)
    rejilla.append(card)
  }
  const actualiza = () => {
    const p = new URLSearchParams()
    const v = document.getElementById("q").value.trim()
    if (v) p.set("q", v)
    if (document.getElementById("f").value) p.set("f", document.getElementById("f").value)
    if (document.getElementById("t").value) p.set("t", document.getElementById("t").value)
    ir(`#/planos${p.toString() ? "?" + p : ""}`)
  }
  const qin = document.getElementById("q")
  qin.onkeydown = (e) => { if (e.key === "Enter") actualiza() }
  qin.focus(); qin.setSelectionRange(qin.value.length, qin.value.length)
  for (const id of ["f", "t"]) document.getElementById(id).onchange = actualiza
}

/* ------------------------------------------------------------ planos: visor */

async function vistaPlano(id, q) {
  const p = await api(`/api/plano/${id}`)
  let pagina = +(q.get("p") || 1)
  const busqueda = q.get("q") || ""
  if (!ordenPlanos.length) ordenPlanos = (await una("/api/planos")).planos.map((x) => x.id)
  const pos = ordenPlanos.indexOf(id)
  const anterior = pos > 0 ? ordenPlanos[pos - 1] : null
  const siguiente = pos >= 0 && pos < ordenPlanos.length - 1 ? ordenPlanos[pos + 1] : null
  vista.innerHTML = `
    <div class="plano">
      <div class="izq">
        <div class="barra">
          <button id="volver" title="Volver a la cuadrícula">▦ Cuadrícula</button>
          <button id="ant" ${anterior ? "" : "disabled"}>◀</button>
          <button id="sig" ${siguiente ? "" : "disabled"}>▶</button>
          <b>${esc(p.codigo)}</b> <span style="color:var(--suave)">${esc(p.nombre)}</span>
          <span style="margin-left:auto"></span>
          ${p.paginas > 1 ? `<select id="pag">${Array.from({ length: p.paginas }, (_, i) => `<option value="${i + 1}" ${i + 1 === pagina ? "selected" : ""}>página ${i + 1}</option>`).join("")}</select>` : ""}
          <button id="menos">−</button><button id="ajustar">Ajustar</button><button id="mas">+</button>
          <label><input type="checkbox" id="verGlobos" checked> globos</label>
        </div>
        <div class="visor" id="visor"><div class="lienzo" id="lienzo"><img id="img" alt=""><div class="capa" id="capa"></div></div></div>
      </div>
      <aside class="panel">
        <input type="search" id="buscar" placeholder="Buscar: cota (N170) o texto" value="${esc(busqueda)}" style="width:100%">
        <div id="estadoBusqueda" style="font-size:12px;color:var(--suave);margin:4px 0"></div>
        <ul class="resultados" id="resultados"></ul>
        <div id="cota"></div>
        <h3>Plano</h3>
        <div class="ruta">${esc(p.ruta)}</div>
        <p>${tagPlano(p)}</p>
        <div id="infoGlobos" style="font-size:12.5px"></div>
        ${p.local ? "" : `<div class="alerta">${esc(p.onedrive)}</div>`}
        <p><a href="#/piezas/${esc(p.codigo)}">Ver la ficha de la pieza ${esc(p.codigo)} →</a></p>
        <details><summary>Páginas (biblioteca)</summary>
          <table><tr><th>Pág.</th><th>Tamaño (pt)</th><th>Imágenes</th><th>Caracteres</th></tr>
          ${p.detalle_paginas.map((x) => `<tr><td>${x.pagina}</td><td>${Math.round(x.ancho_pt || 0)}×${Math.round(x.alto_pt || 0)}</td><td>${x.imagenes ?? ""}</td><td>${x.caracteres}</td></tr>`).join("")}</table>
        </details>
      </aside>
    </div>`
  const navega = (otro, extra = "") => ir(`#/planos/${otro}${extra}`)
  document.getElementById("volver").onclick = () => ir(ultimaRejilla)
  if (anterior) document.getElementById("ant").onclick = () => navega(anterior)
  if (siguiente) document.getElementById("sig").onclick = () => navega(siguiente)
  const selPag = document.getElementById("pag")
  if (selPag) selPag.onchange = () => navega(id, `?p=${selPag.value}${busqueda ? `&q=${encodeURIComponent(busqueda)}` : ""}`)

  const visor = document.getElementById("visor"), lienzo = document.getElementById("lienzo")
  const img = document.getElementById("img"), capa = document.getElementById("capa")
  const est = { s: 1, x: 0, y: 0, w: 1, h: 1 }
  const aplica = () => { lienzo.style.transform = `translate(${est.x}px,${est.y}px) scale(${est.s})` }
  const ajustar = () => {
    const W = visor.clientWidth, H = visor.clientHeight
    est.s = Math.min(W / est.w, H / est.h); est.x = (W - est.w * est.s) / 2; est.y = (H - est.h * est.s) / 2; aplica()
  }
  const zoom = (k, mx = visor.clientWidth / 2, my = visor.clientHeight / 2) => {
    const s = Math.max(0.02, Math.min(est.s * k, 8)); k = s / est.s
    est.x = mx - (mx - est.x) * k; est.y = my - (my - est.y) * k; est.s = s; aplica()
  }
  const centra = (xn, yn, escala) => {
    const W = visor.clientWidth, H = visor.clientHeight
    est.s = escala ?? Math.max(est.s, Math.min(W / est.w, H / est.h) * 5)
    est.x = W / 2 - xn * est.w * est.s; est.y = H / 2 - yn * est.h * est.s; aplica()
  }
  visor.addEventListener("wheel", (e) => {
    e.preventDefault()
    const r = visor.getBoundingClientRect()
    zoom(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left, e.clientY - r.top)
  }, { passive: false })
  let arrastre = null
  visor.onmousedown = (e) => { arrastre = { x: e.clientX - est.x, y: e.clientY - est.y }; visor.classList.add("arrastrando") }
  window.onmousemove = (e) => { if (arrastre) { est.x = e.clientX - arrastre.x; est.y = e.clientY - arrastre.y; aplica() } }
  window.onmouseup = () => { arrastre = null; visor.classList.remove("arrastrando") }
  document.getElementById("mas").onclick = () => zoom(1.4)
  document.getElementById("menos").onclick = () => zoom(1 / 1.4)
  document.getElementById("ajustar").onclick = ajustar

  const listo = new Promise((ok) => {
    img.onload = () => { est.w = img.naturalWidth; est.h = img.naturalHeight; lienzo.style.width = est.w + "px"; lienzo.style.height = est.h + "px"; ajustar(); ok(true) }
    img.onerror = async () => {
      const r = await fetch(img.src); const msg = await r.text()
      visor.innerHTML = `<div class="vacio" style="color:#dde">No se puede dibujar el plano: ${esc(msg)}</div>`; ok(false)
    }
  })
  img.src = imagenPlano(p, pagina, "grande")

  // Globos: del .icp o, sin él, de las lecturas automáticas
  const g = await api(`/api/plano/${id}/${pagina}/globos`)
  const info = document.getElementById("infoGlobos")
  const detalleGlobos = g.detalle ? `<span style="color:var(--suave)">${esc(g.detalle)}</span>` : ""
  info.innerHTML = g.metodo === "lectura"
    ? `<b>${g.globos.length} números leídos</b><br>${detalleGlobos}`
    : g.metodo
      ? `<b>${g.globos.length} globos</b> del <code>${esc(g.icp)}</code><br>${detalleGlobos}`
      : detalleGlobos || "Sin globos ni números leídos en esta página."
  await listo
  const radio = Math.min(est.w, est.h) * 0.0085
  // En los planos limpios el globo no está dibujado: se reconstruye con su número y una línea hasta la cota.
  const sinDibujar = g.metodo === "aproximada" || g.metodo === "gemela"
  const claseGlobo = sinDibujar ? "aprox" : g.metodo === "lectura" ? "lectura" : ""
  const marcadores = []
  if (sinDibujar) {
    const lineas = g.globos.filter((b) => b.px != null).map((b) => `<line x1="${b.x * est.w}" y1="${b.y * est.h}" x2="${b.px * est.w}" y2="${b.py * est.h}"/>`).join("")
    const svg = h(`<svg class="lineas-globo" viewBox="0 0 ${est.w} ${est.h}" stroke-width="${radio * 0.14}">${lineas}</svg>`)
    capa.append(svg); marcadores.push(svg)
  }
  for (const b of g.globos) {
    const d = h(`<div class="globo ${claseGlobo}" title="${g.metodo === "lectura" ? "Lectura automática" : "Globo"} ${esc(b.etiqueta)}"></div>`)
    const r = g.metodo === "lectura" ? Math.max(b.w * est.w, b.h * est.h) * 0.62 : radio
    Object.assign(d.style, { left: b.x * 100 + "%", top: b.y * 100 + "%", width: r * 2 + "px", height: r * 2 + "px" })
    if (sinDibujar) {
      d.textContent = b.etiqueta
      d.style.fontSize = radio * (b.etiqueta.length <= 3 ? 1 : b.etiqueta.length === 4 ? 0.8 : 0.6) + "px"
    }
    d.onmousedown = (e) => e.stopPropagation()
    d.onclick = () => { marcadores.forEach((m) => m.classList.remove("sel")); d.classList.add("sel"); mostrarCota(p.codigo, b.etiqueta, p.componente) }
    capa.append(d); marcadores.push(d)
  }
  document.getElementById("verGlobos").onchange = (e) => marcadores.forEach((m) => { m.style.display = e.target.checked ? "" : "none" })

  // Búsqueda dentro del plano
  const caja = document.getElementById("buscar")
  const buscar = async () => {
    const texto = caja.value.trim()
    capa.querySelectorAll(".marca-res").forEach((m) => m.remove())
    document.getElementById("resultados").innerHTML = ""
    document.getElementById("estadoBusqueda").textContent = texto ? "Buscando…" : ""
    if (!texto) return
    const r = await api(`/api/plano/${id}/buscar?q=${encodeURIComponent(texto)}`)
    const aqui = r.resultados.filter((x) => x.pagina === pagina)
    const otras = [...new Set(r.resultados.filter((x) => x.pagina !== pagina).map((x) => x.pagina))]
    document.getElementById("estadoBusqueda").innerHTML =
      `${r.resultados.length} resultado(s)${otras.length ? ` · también en página ${otras.join(", ")}` : ""}` +
      (r.resultados.length === 0 ? `<br>${esc(motivoSinResultados(p))}` : "")
    const ul = document.getElementById("resultados")
    r.resultados.forEach((x, i) => {
      const li = h(`<li>p.${x.pagina} · <b>${esc(x.texto)}</b> <span class="chip">${esc(x.tipo)}</span></li>`)
      li.onclick = () => {
        if (x.pagina !== pagina) return navega(id, `?p=${x.pagina}&q=${encodeURIComponent(texto)}`)
        capa.querySelectorAll(".marca-res").forEach((m) => m.classList.remove("actual"))
        marcasRes[i]?.classList.add("actual")
        centra(x.x + x.w / 2, x.y + x.h / 2)
      }
      ul.append(li)
    })
    const marcasRes = r.resultados.map((x) => {
      if (x.pagina !== pagina) return null
      const m = h(`<div class="marca-res"></div>`)
      const minimo = 14 / est.w
      Object.assign(m.style, { left: x.x * 100 + "%", top: x.y * 100 + "%", width: Math.max(x.w, minimo) * 100 + "%", height: Math.max(x.h, minimo * est.w / est.h) * 100 + "%" })
      capa.append(m); return m
    })
    if (r.cota && r.cota.medidas) mostrarCota(p.codigo, r.cota.cota, p.componente)
    if (aqui.length) { const x = aqui[0]; marcasRes[r.resultados.indexOf(x)]?.classList.add("actual"); centra(x.x + x.w / 2, x.y + x.h / 2) }
  }
  caja.onkeydown = (e) => { if (e.key === "Enter") buscar() }
  if (busqueda) buscar()
}

function motivoSinResultados(p) {
  if (p.tag === "icp") return "No está en el .icp ni en el texto del plano."
  if (p.tag === "globos") return `La lectura es automática: ${p.leidos} leídos de ${p.detectados} globos. Puede ser uno de los que no se han leído.`
  if (p.tag === "numerado") return "La lectura es automática: puede no haberse leído o no estar en este plano."
  if (p.tag === "nada") return p.con_texto ? "Este plano no tiene globos ni numeración: solo se busca en su texto." : "Este plano no tiene globos, numeración ni texto: no se puede buscar."
  return "Este plano aún no se ha leído (leer_planos.py)."
}

// `componentePlano` dice de qué pieza es el plano en un libro con dos (3288). El del conjunto no es de ninguna: se elige.
async function mostrarCota(codigo, cota, componentePlano) {
  const div = document.getElementById("cota")
  const conjunto = componentePlano === "conjunto"
  const pedido = (div.dataset.pedido = String(+(div.dataset.pedido || 0) + 1))
  const dibuja = async (componente) => {
    div.innerHTML = `<div class="bloque">Cargando cota ${esc(cota)}…</div>`
    const consulta = new URLSearchParams({ c: cota })
    if (componente) consulta.set("componente", componente)
    const r = await api(`/api/pieza/${codigo}/cota?${consulta}`)
    if (!div.isConnected || div.dataset.pedido !== pedido) return // se ha cambiado de pantalla o de globo mientras cargaba
    const titulo = `<b>Cota ${esc(cota)} · pieza ${esc(codigo)}${componente ? ` · ${esc(r.componentes.find((x) => x.id === componente)?.etiqueta)}` : ""}</b>`
    const botones = conjunto ? `<div class="selectores">${r.componentes.map((x) => `<button data-componente="${esc(x.id)}" class="${x.id === componente ? "activo" : ""}">${esc(x.etiqueta)} · ${num(x.valores)} valores</button>`).join("")}</div>` : ""
    if (conjunto && !componente) {
      div.innerHTML = `<div class="bloque">${titulo}<div class="nota">Este plano es el conjunto, y en cada pieza este número es otra cota. Elige cuál mirar:</div>${botones}</div>`
    } else {
      const info = r.info
      const nom = info.nominal[0]
      const enlace = `<a href="#/piezas/${esc(codigo)}?c=${encodeURIComponent(cota)}${r.componente ? `&componente=${esc(r.componente)}` : ""}">Ver evolución completa →</a>`
      div.innerHTML = `<div class="bloque">${titulo}${botones}
        ${info.medidas ? `<div>${num(info.medidas)} medidas en ${info.documentos} informes · ${cuantasCorrecciones(r.correcciones.length)}
          ${nom ? `<br>Nominal ${nom[0]} (${nom[1] >= 0 ? "+" : ""}${nom[1]} / ${nom[2]})` : ""}
          ${info.excluidas ? `<br><span class="chip naranja">${info.excluidas} excluidas (RAND, ceros, atípicos)</span>` : ""}</div>
          <div id="graficaCota"></div>
          ${r.elemento ? `<div class="nota">Pestaña ${esc(r.hoja)} · ${esc(r.elementos.find((x) => x.id === r.elemento)?.etiqueta)}</div>` : `<div class="nota">${r.excluidos.length ? `Todos sus valores están excluidos: no hay ninguno que dibujar.` : "Sin valores con muestreo identificable."}</div>`}
          ${enlace}`
          : `<div style="color:var(--suave)">Sin medidas con ese número en ${r.componente ? "esta pieza" : "los informes DR de la pieza"}. Los números de globo son locales a cada plano: puede ser otra hoja del plano.</div>`}</div>`
      if (info.medidas && r.elemento) {
        graficaLineas(document.getElementById("graficaCota"), { ...datosGrafica(r, r.cavidades.slice(0, MAX_CAVIDADES_VISIBLES)), alto: 220, margen: 56 })
      }
    }
    div.querySelectorAll("[data-componente]").forEach((b) => { b.onclick = () => dibuja(b.dataset.componente) })
  }
  await dibuja(conjunto ? null : componentePlano)
}

/* ------------------------------------------------------------ piezas */

let ultimasPiezas = "#/piezas"
let grafoPiezasVivo = null
const featuresDe = (p) => [...new Set(p.features)]

// Las cifras que se comparan entre piezas: [campo, título de la columna].
const CIFRAS = [["documentos", "Ficheros"], ["planos", "Planos"], ["muestreos", "Muestreos"], ["cotas", "Cotas medidas"],
  ["correcciones", "Pasos de corrección"], ["hallazgos", "Hallazgos"], ["casos", "Casos de referencia"]]
let ordenNumeros = { campo: "codigo", sentido: 1 }
const SUBPESTANAS = { "": "Cuadrícula", numeros: "Números", grafo: "Grafo" }
// Un solo tag por pieza: qué datos tiene. En rojo, las que no tienen medidas.
const CLASE_TAG_PIEZA = { correcciones: "verde", medidas: "naranja", nada: "rojo" }

function tagPieza(p, tags) {
  return `<span class="chip ${CLASE_TAG_PIEZA[p.tag]}" ${p.tag_motivo ? `title="${esc(p.tag_motivo)}"` : ""}>${esc(tags[p.tag])}</span>`
}
function familiaPieza(p, familias) {
  const f = familias[p.familia]
  return f ? `<span class="chip morado" title="${esc(f.fuente)}">${esc(p.familia)}${f.supuesta ? " (suposición)" : ""}</span>` : ""
}

async function vistaPiezas(sub, q) {
  const aqui = ultimasPiezas = location.hash || "#/piezas"
  const { piezas, tags, familias } = await una("/api/piezas")
  if ((location.hash || "#/piezas") !== aqui) return // se ha cambiado de pantalla mientras cargaba
  const texto = q.get("q") || ""
  const feature = q.get("f") || ""
  const tag = q.get("t") || ""
  const familia = q.get("fa") || ""
  const features = [...new Set(piezas.flatMap(featuresDe))].sort()
  const consulta = q.toString() ? `?${q}` : ""
  vista.innerHTML = `
    <div class="barra">
      <input type="search" id="q" placeholder="Pieza, feature, familia, fichero CAD…" value="${esc(texto)}" style="width:320px">
      <select id="f"><option value="">Todos los features</option>${features.map((f) => `<option ${f === feature ? "selected" : ""}>${esc(f)}</option>`).join("")}</select>
      <select id="t"><option value="">Todos los tags</option>${Object.entries(tags).map(([k, v]) => `<option value="${k}" ${k === tag ? "selected" : ""}>${esc(v)} (${piezas.filter((p) => p.tag === k).length})</option>`).join("")}</select>
      <select id="fa"><option value="">Todas las familias</option>${Object.keys(familias).map((k) => `<option ${k === familia ? "selected" : ""}>${esc(k)}</option>`).join("")}</select>
      <span class="subpestanas">
        ${Object.entries(SUBPESTANAS).map(([k, v]) => `<a href="#/piezas${k && "/" + k}${consulta}" class="${k === sub ? "activo" : ""}">${v}</a>`).join("")}
      </span>
    </div>
    <div id="cuerpo"></div>`
  const t = texto.toLowerCase()
  const lista = piezas.filter((p) => (!feature || p.features.includes(feature)) && (!tag || p.tag === tag) && (!familia || p.familia === familia) &&
    (!texto || `${p.codigo} ${p.features.join(" ")} ${p.carpetas.join(" ")} ${p.cad.join(" ")} ${p.familia ?? ""}`.toLowerCase().includes(t)))
  const cuerpo = document.getElementById("cuerpo")
  if (!lista.length) cuerpo.innerHTML = `<div class="vacio">Ninguna pieza coincide.</div>`
  else if (sub === "numeros") tablaNumeros(cuerpo, lista, tags, familias)
  else if (sub === "grafo") await grafoDePiezas(cuerpo, lista)
  else rejillaPiezas(cuerpo, lista, tags, familias)
  const actualiza = () => {
    const p = new URLSearchParams()
    const v = document.getElementById("q").value.trim()
    if (v) p.set("q", v)
    for (const id of ["f", "t", "fa"]) if (document.getElementById(id).value) p.set(id, document.getElementById(id).value)
    ir(`#/piezas${sub && "/" + sub}${p.toString() ? "?" + p : ""}`)
  }
  const qin = document.getElementById("q")
  qin.onkeydown = (e) => { if (e.key === "Enter") actualiza() }
  qin.focus(); qin.setSelectionRange(qin.value.length, qin.value.length)
  for (const id of ["f", "t", "fa"]) document.getElementById(id).onchange = actualiza
}

function rejillaPiezas(cuerpo, lista, tags, familias) {
  const rejilla = h(`<div class="rejilla"></div>`)
  for (const p of lista) {
    const card = h(`<div class="tarjeta ${p.tag === "nada" ? "sin-busqueda" : ""}" title="${esc(p.cad.join(" · "))}">
      <div class="mini"><img loading="lazy" alt="" src="/cad/${esc(p.codigo)}.jpg"></div>
      <div class="pie"><b>${esc(p.codigo)}</b> · ${esc(featuresDe(p).join(" · "))}
        <div class="nombre">${esc(p.cad.join(" · "))}</div>
        ${tagPieza(p, tags)}${familiaPieza(p, familias)}
        <div class="muestreos-pieza">${p.muestreos ? muestreos(p.muestreos) : p.tag === "nada" ? "0 muestreos" : "Sin muestreos leídos"}</div>
      </div></div>`)
    const img = card.querySelector("img")
    img.onerror = () => { img.replaceWith(h(`<span>sin miniatura</span>`)) }
    card.onclick = () => ir(`#/piezas/${p.codigo}`)
    rejilla.append(card)
  }
  cuerpo.append(rejilla)
}

function tablaNumeros(cuerpo, lista, tags, familias) {
  const { campo, sentido } = ordenNumeros
  const orden = [...lista].sort((a, b) => sentido * (campo === "codigo" ? a.codigo.localeCompare(b.codigo) : a[campo] - b[campo]) || a.codigo.localeCompare(b.codigo))
  const titulo = (c, texto, clase = "") => `<th class="${clase}" data-campo="${c}" title="Ordenar">${texto}${c === campo ? (sentido > 0 ? " ▲" : " ▼") : ""}</th>`
  cuerpo.innerHTML = `<div class="numeros"><table>
    <tr>${titulo("codigo", "Pieza")}<th class="fijo">Feature</th><th class="fijo">Tag</th><th class="fijo">Familia</th>${CIFRAS.map(([c, t]) => titulo(c, t, "cifra-col")).join("")}</tr>
    ${orden.map((p) => `<tr data-codigo="${esc(p.codigo)}"><td><b>${esc(p.codigo)}</b></td><td>${esc(featuresDe(p).join(" | "))}</td><td>${tagPieza(p, tags)}</td><td>${familiaPieza(p, familias)}</td>${CIFRAS.map(([c]) => `<td class="cifra-col ${p[c] ? "" : "cero"}">${num(p[c])}</td>`).join("")}</tr>`).join("")}
  </table></div>`
  cuerpo.querySelectorAll("th[data-campo]").forEach((th) => {
    th.onclick = () => {
      const c = th.dataset.campo
      // La primera pulsación en una cifra pone arriba las piezas con más.
      ordenNumeros = c === campo ? { campo, sentido: -sentido } : { campo: c, sentido: c === "codigo" ? 1 : -1 }
      tablaNumeros(cuerpo, lista, tags, familias)
    }
  })
  cuerpo.querySelectorAll("tr[data-codigo]").forEach((tr) => { tr.onclick = () => ir(`#/piezas/${tr.dataset.codigo}`) })
}

/* Grafo de piezas y features. Pinta menos que el de la pestaña Grafo, pero con la misma línea. */

const COLOR_LINEA = "rgba(176, 196, 236, .8)"
const COLOR_IDENTICOS = "#3ecf8e"
const COLOR_FAMILIA = "#b07cf7"
const COLOR_SELECCION = "rgba(255, 200, 90, .95)"
const RADIO_PIEZA = 14
const idDe = (extremo) => extremo.id ?? extremo
const LEYENDA = `<h2>Piezas, features y familias</h2>
  <p><span class="chip" style="background:#f5a524;color:#111">Naranja</span> es un feature; <span class="chip" style="background:${COLOR_FAMILIA};color:#111">morado</span>, una familia; cada imagen es una pieza.</p>
  <p><span class="muestra-linea"></span> La pieza está en ese feature. Una pieza con dos líneas está en dos features y los une.</p>
  <p><span class="muestra-linea identicos"></span> Las dos piezas tienen ficheros idénticos, como un utillaje o un plano. Cuantos más, más gruesa. No cuentan los README, la caché del navegador ni los ficheros vacíos.</p>
  <p><span class="muestra-linea familia"></span> La pieza es de esa familia. Las familias no son un dato de los ficheros: son agrupaciones nuestras, y la de Isomask es una suposición.</p>
  <p>Pulsa un nodo para ver sus conexiones.</p>`

async function grafoDePiezas(cuerpo, lista) {
  const datos = await una("/api/grafo/piezas")
  if (!cuerpo.isConnected) return // se ha cambiado de pantalla mientras cargaba
  const visibles = new Set(lista.map((p) => `pieza:${p.codigo}`))
  const aristas = datos.aristas.filter((a) => visibles.has(a.source) && (a.tipo !== "identicos" || visibles.has(a.target))).map((a) => ({ ...a }))
  const piezasTotales = datos.nodos.filter((n) => n.tipo === "pieza").length
  const conPieza = new Set(aristas.map((a) => a.target))
  // Sin filtros se ven todos los features, también el que no tiene piezas.
  const nodos = datos.nodos.filter((n) => visibles.has(n.id) || (n.tipo !== "pieza" && (lista.length === piezasTotales || conPieza.has(n.id)))).map((n) => ({ ...n }))
  const porId = Object.fromEntries(nodos.map((n) => [n.id, n]))
  cuerpo.innerHTML = `<div class="grafo grafo-piezas"><div id="lienzo-grafo"></div><aside class="lateral" id="lateral">${LEYENDA}</aside></div>`
  const el = document.getElementById("lienzo-grafo"), lateral = document.getElementById("lateral")
  const fotos = {}
  for (const n of nodos) if (n.tipo === "pieza") { fotos[n.id] = new Image(); fotos[n.id].src = `/cad/${n.etiqueta}.jpg` }
  let seleccion = null, vecinos = new Set(), asentado = false
  // Sin posiciones todavía, el encuadre daría NaN y dejaría la vista rota.
  const encuadra = () => { if (el.isConnected && nodos[0]?.x != null) g.zoomToFit(0, 40) }

  const pintaGrupo = (n, ctx) => {
    const texto = n.supuesta ? `${n.etiqueta} ?` : n.etiqueta
    ctx.font = "600 6px system-ui"
    n.ancho = ctx.measureText(texto).width + 10
    ctx.fillStyle = n.tipo === "familia" ? COLOR_FAMILIA : "#f5a524"
    ctx.beginPath(); ctx.roundRect(n.x - n.ancho / 2, n.y - 6, n.ancho, 12, 6); ctx.fill()
    ctx.fillStyle = "#111"; ctx.textAlign = "center"; ctx.textBaseline = "middle"
    ctx.fillText(texto, n.x, n.y + .3)
  }
  const pintaPieza = (n, ctx) => {
    ctx.save()
    ctx.beginPath(); ctx.arc(n.x, n.y, RADIO_PIEZA, 0, 2 * Math.PI); ctx.fillStyle = "#fff"; ctx.fill(); ctx.clip()
    const foto = fotos[n.id]
    if (foto.complete && foto.naturalWidth) ctx.drawImage(foto, n.x - RADIO_PIEZA * 1.25, n.y - RADIO_PIEZA * .89, RADIO_PIEZA * 2.5, RADIO_PIEZA * 1.78)
    ctx.restore()
    ctx.beginPath(); ctx.arc(n.x, n.y, RADIO_PIEZA, 0, 2 * Math.PI)
    ctx.lineWidth = n.id === seleccion ? 1.6 : .6; ctx.strokeStyle = n.id === seleccion ? "#ffc85a" : "#8d96ab"; ctx.stroke()
    ctx.font = "600 5.5px system-ui"; ctx.fillStyle = "#e6e9ef"; ctx.textAlign = "center"; ctx.textBaseline = "top"
    ctx.fillText(n.etiqueta, n.x, n.y + RADIO_PIEZA + 1.5)
  }
  const g = ForceGraph()(el).backgroundColor("#16181d").autoPauseRedraw(false)
    .warmupTicks(200).cooldownTicks(60)
    .onEngineStop(() => { if (!asentado) { asentado = true; encuadra() } })
    .nodeCanvasObject((n, ctx) => {
      ctx.globalAlpha = seleccion && n.id !== seleccion && !vecinos.has(n.id) ? .2 : 1
      n.tipo === "pieza" ? pintaPieza(n, ctx) : pintaGrupo(n, ctx)
      ctx.globalAlpha = 1
    })
    .nodePointerAreaPaint((n, color, ctx) => {
      ctx.fillStyle = color; ctx.beginPath()
      if (n.tipo !== "pieza") ctx.rect(n.x - (n.ancho || 40) / 2, n.y - 6, n.ancho || 40, 12)
      else ctx.arc(n.x, n.y, RADIO_PIEZA, 0, 2 * Math.PI)
      ctx.fill()
    })
    .linkColor((l) => {
      const mia = seleccion && (idDe(l.source) === seleccion || idDe(l.target) === seleccion)
      if (mia) return COLOR_SELECCION
      if (seleccion) return "rgba(120, 130, 150, .15)"
      return l.tipo === "identicos" ? COLOR_IDENTICOS : l.tipo === "familia" ? COLOR_FAMILIA : COLOR_LINEA
    })
    .linkWidth((l) => (l.tipo === "identicos" ? 1.2 + Math.sqrt(l.ficheros.length) * .7 : 1.6))
    .linkLineDash((l) => (l.tipo === "identicos" ? [4, 3] : l.tipo === "familia" ? [2, 2] : null))
    .linkLabel((l) => (l.tipo === "identicos" ? `${esc(idDe(l.source).slice(6))} y ${esc(idDe(l.target).slice(6))}: ${l.ficheros.length} fichero(s) idéntico(s)` : ""))
    .onNodeHover((n) => { el.style.cursor = n ? "pointer" : "" })
    .onNodeClick((n) => selecciona(n.id))
    .onBackgroundClick(() => { seleccion = null; vecinos = new Set(); lateral.innerHTML = LEYENDA })
  g.d3Force("charge").strength(-220).distanceMax(400)
  g.d3Force("link").distance((l) => (l.tipo === "identicos" ? 70 : 55)).strength((l) => (l.tipo === "identicos" ? .12 : .55))

  function selecciona(id) {
    seleccion = id
    const mias = aristas.filter((a) => idDe(a.source) === id || idDe(a.target) === id)
    const otro = (a) => (idDe(a.source) === id ? idDe(a.target) : idDe(a.source))
    vecinos = new Set(mias.map(otro))
    lateral.innerHTML = fichaNodo(porId[id], mias, otro)
    lateral.querySelectorAll("a[data-nodo]").forEach((a) => { a.onclick = (e) => { e.preventDefault(); selecciona(a.dataset.nodo) } })
  }
  g.graphData({ nodes: nodos, links: aristas })
  grafoPiezasVivo = g
  // Ocupa lo que deja la barra, también al cambiar el tamaño de la ventana, y encuadra la red entera.
  const observador = new ResizeObserver(() => {
    if (!el.isConnected) return observador.disconnect()
    const alto = vista.clientHeight - document.querySelector(".barra").offsetHeight
    cuerpo.firstElementChild.style.height = `${alto}px`
    g.width(el.clientWidth).height(alto)
    setTimeout(encuadra, 50) // tras aplicar el tamaño nuevo
  })
  observador.observe(vista)
  setTimeout(encuadra, 200) // la primera colocación ya está hecha: no se espera a que se pare la animación
}

function fichaNodo(n, mias, otro) {
  const enlace = (id, n2) => `<a href="#" data-nodo="${esc(id)}">${esc(n2)}</a>`
  const nombre = (id) => id.split(":")[1]
  if (n.tipo === "familia") {
    return `<h2>${esc(n.etiqueta)}</h2><p>${esc(n.fuente)}</p>
      <h3>${mias.length} pieza(s)</h3><ul>${mias.map((a) => `<li>${enlace(otro(a), nombre(otro(a)))}</li>`).join("")}</ul>`
  }
  if (n.tipo === "feature") {
    return `<h2>${esc(n.etiqueta)}</h2>${mias.length
      ? `<h3>${mias.length} pieza(s)</h3><ul>${mias.map((a) => `<li>${enlace(otro(a), nombre(otro(a)))} · ${num(a.ficheros)} fichero(s)</li>`).join("")}</ul>`
      : "<p>Sin piezas: en <code>Exemples</code> este feature no tiene ninguna carpeta de pieza.</p>"}`
  }
  const features = mias.filter((a) => a.tipo === "feature")
  const identicos = mias.filter((a) => a.tipo === "identicos")
  const familia = mias.find((a) => a.tipo === "familia")
  return `<h2>Pieza ${esc(n.etiqueta)}</h2>
    <img class="foto-pieza" alt="" src="/cad/${esc(n.etiqueta)}.jpg">
    <p><a href="#/piezas/${esc(n.etiqueta)}">Abrir la ficha →</a></p>
    ${familia ? `<h3>Familia</h3><p>${enlace(otro(familia), nombre(otro(familia)))}</p>` : ""}
    <h3>Features</h3><ul>${features.map((a) => `<li>${enlace(otro(a), nombre(otro(a)))} · ${num(a.ficheros)} fichero(s)</li>`).join("")}</ul>
    <h3>Ficheros idénticos con otras piezas</h3>
    ${identicos.length ? identicos.map((a) => `<p><b>${enlace(otro(a), nombre(otro(a)))}</b></p><ul>${a.ficheros.map((f) => `<li>${esc(f.nombre)} <span class="chip">${esc(f.carpeta)}</span></li>`).join("")}</ul>`).join("") : "<p>Ninguno.</p>"}`
}

async function vistaPieza(codigo, q) {
  vista.innerHTML = `<section class="contenido" id="contenido"><div class="vacio">Cargando ${esc(codigo)}…</div></section>`
  const aqui = location.hash
  const d = await api(`/api/pieza/${codigo}`)
  const { tags, familias } = await una("/api/piezas")
  if (location.hash !== aqui) return // se ha cambiado de pantalla mientras cargaba
  const c = document.getElementById("contenido")
  const correcciones = {}
  d.cadenas.forEach((x) => { correcciones[x.cota] = (correcciones[x.cota] || 0) + 1 })
  const cotaIni = q.get("c") || [...d.cotas].sort((a, b) => (correcciones[b.cota] || 0) - (correcciones[a.cota] || 0) || b.muestreos - a.muestreos)[0]?.cota
  // Con dos piezas en el libro (3288), la lista y sus recuentos son los de la que se está mirando.
  const opcionesCota = (componente, elegida) => d.cotas
    .filter((x) => !componente || x.por_componente[componente] || x.cota === elegida)
    .map((x) => {
      const n = componente ? x.por_componente[componente] ?? { medidas: 0, muestreos: 0 } : x
      return `<option value="${esc(x.cota)}" ${x.cota === elegida ? "selected" : ""}>${esc(x.cota)} — ${num(n.medidas)} medidas, ${n.muestreos} muestreos</option>`
    }).join("")
  c.innerHTML = `
    <p><button id="volver" title="Volver a la cuadrícula">▦ Cuadrícula</button></p>
    <h2>Pieza ${esc(codigo)}</h2>
    <div>${tagPieza(d.resumen, tags)}${familiaPieza(d.resumen, familias)}${d.resumen.features.map((f) => `<span class="chip azul">${esc(f)}</span>`).join("")} ${d.resumen.carpetas.map((f) => `<span class="chip">${esc(f)}</span>`).join("")}</div>
    ${d.resumen.tag_motivo ? `<div class="nota">${esc(d.resumen.tag_motivo)}</div>` : ""}
    ${d.identidad.length ? `<div class="bloque md"><b>Identidad</b> <span class="chip">identidad-piezas.md</span>${md(d.identidad.join("\n"))}</div>` : ""}
    <div class="bloque">
      <b>Evolución de una cota</b> <span class="chip">informes intern.NN · un valor por cavidad y muestreo</span>
      <div class="selectores">
        <label>Cota <select id="selCota">${opcionesCota(null, cotaIni)}</select></label>
        <span id="infoCota" class="nota"></span>
      </div>
      <div id="evolucion"></div>
    </div>
    <div class="bloque"><b>Cadena de correcciones</b> <span class="chip">cadena_correccion</span> <span id="filtroCad"></span>
      <div style="max-height:360px;overflow:auto"><table id="tablaCad"></table></div></div>
    <div class="bloque"><b>Muestreos</b> <span class="chip">informes DR de 4- Metrologia</span>
      <div style="max-height:320px;overflow:auto"><table>
      <tr><th>Serie/muestreo</th><th>Ficheros</th><th>Medidas</th><th>Excluidas</th><th>Fechas de informe</th><th>Papel de las hojas</th></tr>
      ${d.muestreos.map((m) => `<tr><td><b>${esc(m.clave)}</b></td><td>${m.documentos.map(esc).join("<br>")}</td><td>${num(m.medidas)}</td><td>${num(m.excluidas)}</td>
        <td>${m.fechas.map(esc).join("<br>")}</td><td>${Object.entries(m.papeles).map(([k, v]) => `${esc(k)}: ${num(v)}`).join("<br>")}</td></tr>`).join("")}
      </table></div>
      ${d.sin_muestreo.length ? `<details><summary>${d.sin_muestreo.length} ficheros con medidas DR sin intern.NN en el nombre</summary>${d.sin_muestreo.map(esc).join("<br>")}</details>` : ""}
    </div>
    <div class="bloque"><b>Hallazgos e incongruencias</b> <span class="chip">hallazgos.jsonl</span>
      <table><tr><th>Id</th><th>Tipo</th><th>Relevancia</th><th>Estado</th><th>Afirmación</th></tr>
      ${d.hallazgos.map((x) => `<tr><td><a href="#/grafo?n=${encodeURIComponent(x.id)}">${esc(x.id)}</a></td><td>${esc(x.tipo)}</td><td>${esc(x.relevancia)}</td><td>${esc(x.estado)}</td><td>${esc((x.afirmacion || "").slice(0, 400))}</td></tr>`).join("")}</table></div>
    ${d.casos.length ? `<div class="bloque"><b>Casos de referencia</b> <span class="chip">casos-referencia.jsonl</span><table><tr><th>Id</th><th>Fichero</th><th>Celda</th><th>Tratamiento</th><th>Motivo</th></tr>
      ${d.casos.map((x) => `<tr><td>${esc(x.id)}</td><td>${esc((x.ruta || "").split("/").pop())}</td><td>${esc(x.hoja)}!${esc(x.celda)}</td><td>${esc(x.tratamiento_esperado)}</td><td>${esc(x.motivo)}</td></tr>`).join("")}</table></div>` : ""}
    <div class="bloque"><b>Ficheros por carpeta</b> <span class="chip">documento</span>
      <table><tr><th>Carpeta</th><th>Ficheros</th><th>Con contenido extraído</th><th>Solo metadatos</th><th>Sin texto</th><th>Duplicados</th></tr>
      ${d.carpetas.map((x) => `<tr><td>${esc(x.carpeta_norm)}</td><td>${x.n}</td><td>${x.extraidos}</td><td>${x.metadatos}</td><td>${x.sin_texto}</td><td>${x.duplicados}</td></tr>`).join("")}</table>
      <p>${d.extensiones.map((x) => `<span class="chip">${esc(x.ext || "sin ext.")} ${x.n}</span>`).join("")}</p></div>`
  document.getElementById("volver").onclick = () => ir(ultimasPiezas)

  let componenteActual = null
  const cadenasActuales = () => d.cadenas.filter((x) => !componenteActual || !x.componente || x.componente === componenteActual)
  const tablaCad = (cota) => {
    const todas = cadenasActuales()
    const filas = cota ? todas.filter((x) => x.cota === cota) : todas
    document.getElementById("filtroCad").innerHTML = cota ? `cota ${esc(cota)}: ${filas.length} de ${todas.length} · <a href="#" id="todasCad">ver todas</a>` : `${todas.length} pasos`
    document.getElementById("tablaCad").innerHTML = `<tr><th>Cota</th><th>Corrección</th><th>Fecha</th><th>Origen</th><th>Validación</th><th>Estado</th><th>Avisos</th></tr>` +
      filas.map((x) => `<tr><td><a href="#" data-cota="${esc(x.cota)}">${esc(x.cota)}</a></td><td>${esc(x.numero ?? "")}</td><td>${esc(x.fecha_correccion ?? "")}</td>
        <td>${x.origen_muestreo != null ? `intern.${String(x.origen_muestreo).padStart(2, "0")} · ${x.origen_fuera ?? "?"}/${x.origen_n ?? "?"} fuera` : "—"}</td>
        <td>${x.validacion_muestreo != null ? `intern.${String(x.validacion_muestreo).padStart(2, "0")} · ${x.validacion_fuera ?? "?"}/${x.validacion_n ?? "?"} fuera` : "—"}</td>
        <td>${esc(x.validacion_estado ?? "")}</td><td style="font-size:11px;color:var(--suave)">${esc((JSON.parse(x.avisos || "[]") || []).join("; "))}</td></tr>`).join("")
    document.querySelectorAll("#tablaCad a[data-cota]").forEach((a) => { a.onclick = (e) => { e.preventDefault(); document.getElementById("selCota").value = a.dataset.cota; dibuja() } })
    const verTodas = document.getElementById("todasCad"); if (verTodas) verTodas.onclick = (e) => { e.preventDefault(); tablaCad(null) }
  }
  // La cabecera, la lista de cotas y la tabla de correcciones siguen a lo que dibuja la gráfica.
  const alCargar = (r) => {
    const sel = document.getElementById("selCota")
    if (!sel) return // se ha cambiado de pantalla mientras cargaba
    if (r.componente !== componenteActual) {
      componenteActual = r.componente
      sel.innerHTML = opcionesCota(componenteActual, r.info.cota)
    }
    const info = r.info
    document.getElementById("infoCota").textContent = `${num(info.medidas)} medidas · ${info.documentos} ficheros · ${cuantasCorrecciones(r.correcciones.length)}${info.nominal.length > 1 ? " · varias nominales o tolerancias con el mismo número" : ""}`
    tablaCad(cadenasActuales().some((x) => x.cota === info.cota) ? info.cota : null)
  }
  const muestraCota = evolucionCota(document.getElementById("evolucion"), codigo, { componente: q.get("componente"), alCargar })
  const dibuja = () => {
    const cota = document.getElementById("selCota").value
    if (cota) muestraCota(cota)
    else { document.getElementById("evolucion").innerHTML = `<div class="vacio">Sin medidas DR.</div>`; tablaCad(null) }
  }
  document.getElementById("selCota").onchange = dibuja
  dibuja()
}

/* ------------------------------------------------------------ grafo */

const COLORES = {
  feature: "#f5a524", pieza: "#ef5350", hallazgo: "#b07cf7", pregunta: "#3ecf8e", caso: "#7b8496",
  "ficha-pieza": "#4f8ff7", "ficha-feature": "#ff8f4d", docs: "#2ec4c4", conocimiento: "#f2d24b",
  ingesta: "#8bc34a", rag: "#e57bd5", raiz: "#c8ccd6",
}
const NOMBRES = {
  feature: "Feature", pieza: "Pieza", hallazgo: "Hallazgo / incongruencia (I-xxx)", pregunta: "Pregunta abierta (A-xx)",
  caso: "Caso de referencia (CR-xxx)", "ficha-pieza": "Ficha de pieza (.md)", "ficha-feature": "Ficha de feature (.md)",
  docs: "docs/ (.md)", conocimiento: "conocimiento/ (.md)", ingesta: "conocimiento/ingesta", rag: "conocimiento/rag", raiz: "Raíz del repo",
}
let grafoVivo = null
const radioNodo = (n) => 2.5 + Math.sqrt(n.grado || 0) * 0.9

async function vistaGrafo(q) {
  const datos = await una("/api/grafo")
  vista.innerHTML = `<div class="grafo"><div id="lienzo-grafo"></div>
    <div class="controles">
      <input type="search" id="buscaNodo" placeholder="Buscar nodo (3212, I-003, A10, trampas…)">
      <div id="tipos"></div>
      <div style="margin-top:6px">Menciones con peso ≥ <b id="vPeso">2</b><input type="range" id="peso" min="1" max="10" value="2" style="width:100%"></div>
      <label><input type="checkbox" id="etiquetas" checked> nombres</label>
      <div style="color:#8d96ab;margin-top:4px" id="cuentaGrafo"></div>
    </div>
    <aside class="lateral" id="lateral"><h2>Grafo del conocimiento</h2>
      <p>Cada punto es un fichero Markdown, una pieza, un feature, un hallazgo (I-xxx), una pregunta abierta (A-xx) o un caso de referencia.
      Las líneas salen de enlaces entre ficheros y de menciones explícitas en el texto o en los JSONL.</p>
      <p>Pasa el ratón para ver el nombre; pulsa un nodo para ver su contenido y resaltar sus vecinos. Rueda para hacer zoom, arrastra para moverte.</p></aside></div>`
  const activos = new Set(Object.keys(COLORES).filter((t) => t !== "caso"))
  const tipos = document.getElementById("tipos")
  const cuenta = {}
  datos.nodos.forEach((n) => { cuenta[n.tipo] = (cuenta[n.tipo] || 0) + 1 })
  for (const t of Object.keys(COLORES)) {
    if (!cuenta[t]) continue
    const l = h(`<label><input type="checkbox" ${activos.has(t) ? "checked" : ""}><span class="punto" style="background:${COLORES[t]}"></span>${NOMBRES[t]} <span style="color:#7d8699">${cuenta[t]}</span></label>`)
    l.querySelector("input").onchange = (e) => { e.target.checked ? activos.add(t) : activos.delete(t); actualiza() }
    tipos.append(l)
  }
  const el = document.getElementById("lienzo-grafo")
  const ancho = () => el.clientWidth || vista.clientWidth - 420
  let seleccion = null, vecinos = new Set(), enlacesSel = new Set(), hover = null, encuadrado = false
  const g = ForceGraph()(el).width(ancho()).height(vista.clientHeight).backgroundColor("#16181d")
    .nodeId("id").nodeVal((n) => 1 + Math.sqrt(n.grado || 0) * 1.6)
    .nodeLabel(() => "")
    .linkColor((l) => (enlacesSel.has(l) ? COLOR_SELECCION : COLOR_LINEA))
    .linkWidth((l) => (enlacesSel.has(l) ? 1.8 : 0.6))
    .linkDirectionalParticles((l) => (enlacesSel.has(l) ? 2 : 0)).linkDirectionalParticleWidth(2)
    .d3VelocityDecay(0.3).cooldownTicks(400)
    .onEngineStop(() => { if (!encuadrado) { encuadrado = true; g.zoomToFit(500, 40) } })
    .nodeCanvasObject((n, ctx, escala) => {
      const r = radioNodo(n)
      const apagado = seleccion && !vecinos.has(n.id) && n.id !== seleccion
      ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
      ctx.fillStyle = apagado ? "rgba(90,95,110,.35)" : COLORES[n.tipo] || "#ccc"
      if (!apagado) { ctx.shadowColor = COLORES[n.tipo]; ctx.shadowBlur = n.id === seleccion || n === hover ? 18 : 6 }
      ctx.fill(); ctx.shadowBlur = 0
      if (n.id === seleccion) { ctx.lineWidth = 2 / escala; ctx.strokeStyle = "#fff"; ctx.stroke() }
      const mostrar = document.getElementById("etiquetas")?.checked && (escala > 1.6 || n.grado > 45 || n.id === seleccion || (seleccion && vecinos.has(n.id)) || n === hover)
      if (mostrar && !apagado) {
        const t = n.tipo === "pieza" || n.tipo === "hallazgo" || n.tipo === "pregunta" || n.tipo === "caso" ? n.etiqueta : (n.ruta || n.etiqueta).split("/").pop()
        ctx.font = `${Math.max(11 / escala, 1.8)}px system-ui`; ctx.textAlign = "center"; ctx.textBaseline = "top"
        ctx.fillStyle = "rgba(230,233,240,.92)"; ctx.fillText(t, n.x, n.y + r + 1.5)
      }
    })
    .nodePointerAreaPaint((n, color, ctx) => { const r = radioNodo(n) + 1.5; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 2 * Math.PI); ctx.fill() })
    .onNodeHover((n) => {
      hover = n; el.style.cursor = n ? "pointer" : ""
      if (!n) { tooltip.style.display = "none"; return }
      tooltip.innerHTML = `<b>${esc(n.etiqueta)}</b><br><span style="color:${COLORES[n.tipo]}">${esc(NOMBRES[n.tipo] || n.tipo)}</span>
        ${n.ruta ? `<br><span style="color:#9aa">${esc(n.ruta)}</span>` : ""}${n.titulo ? `<br>${esc(n.titulo)}` : ""}
        ${n.estado ? `<br>estado: ${esc(n.estado)}${n.relevancia ? ` · relevancia: ${esc(n.relevancia)}` : ""}` : ""}
        ${n.etiquetas?.length ? `<br>${n.etiquetas.map((e) => `<span class="chip">${esc(e)}</span>`).join("")}` : ""}
        ${n.resumen ? `<br><span style="color:#bbc">${esc(n.resumen)}</span>` : ""}<br><span style="color:#889">${n.grado} conexiones</span>`
      tooltip.style.display = "block"
    })
    .onNodeClick((n) => selecciona(n.id, false))
    .onBackgroundClick(() => { seleccion = null; vecinos = new Set(); enlacesSel = new Set() })
  grafoVivo = g
  g.d3Force("charge").strength(-90).distanceMax(400)
  g.d3Force("link").distance((l) => (l.tipo === "enlace" ? 45 : 70)).strength(0.15)
  el.onmousemove = (e) => { tooltip.style.left = e.clientX + 14 + "px"; tooltip.style.top = e.clientY + 14 + "px" }
  window.onresize = () => { if (grafoVivo === g) g.width(ancho()).height(vista.clientHeight) }

  let enlacesActuales = []
  function actualiza() {
    const peso = +document.getElementById("peso").value
    document.getElementById("vPeso").textContent = peso
    const nodos = datos.nodos.filter((n) => activos.has(n.tipo)).map((n) => ({ ...n }))
    const ids = new Set(nodos.map((n) => n.id))
    enlacesActuales = datos.aristas.filter((a) => ids.has(a.source) && ids.has(a.target) && (a.tipo !== "menciona" || a.peso >= peso)).map((a) => ({ ...a }))
    const previos = new Map(g.graphData().nodes.map((n) => [n.id, n]))
    nodos.forEach((n) => { const p = previos.get(n.id); if (p) { n.x = p.x; n.y = p.y } })
    g.graphData({ nodes: nodos, links: enlacesActuales })
    document.getElementById("cuentaGrafo").textContent = `${nodos.length} nodos · ${enlacesActuales.length} conexiones`
  }
  document.getElementById("peso").oninput = actualiza
  document.getElementById("etiquetas").onchange = () => g.nodeColor(g.nodeColor())

  async function selecciona(id, centrar = true) {
    const nodo = g.graphData().nodes.find((n) => n.id === id)
    seleccion = id; vecinos = new Set(); enlacesSel = new Set()
    for (const l of g.graphData().links) {
      const a = l.source.id ?? l.source, b = l.target.id ?? l.target
      if (a === id || b === id) { vecinos.add(a); vecinos.add(b); enlacesSel.add(l) }
    }
    if (nodo && centrar) { encuadrado = true; g.centerAt(nodo.x, nodo.y, 600); g.zoom(2.5, 600) }
    const lat = document.getElementById("lateral")
    lat.innerHTML = `<div class="vacio">Cargando…</div>`
    const r = await api(`/api/nodo?id=${encodeURIComponent(id)}`)
    const n = r.nodo
    const listaVecinos = [...vecinos].filter((v) => v !== id).map((v) => datos.nodos.find((x) => x.id === v)).filter(Boolean)
      .sort((a, b) => a.tipo.localeCompare(b.tipo) || a.etiqueta.localeCompare(b.etiqueta))
    lat.innerHTML = `<h2>${esc(n.etiqueta)}</h2>
      <div><span class="chip" style="background:${COLORES[n.tipo]};color:#111">${esc(NOMBRES[n.tipo] || n.tipo)}</span> ${n.ruta ? `<code>${esc(n.ruta)}</code>` : ""}</div>
      ${n.tipo === "pieza" ? `<p><a href="#/piezas/${esc(n.etiqueta)}">Abrir la ficha de la pieza →</a></p>` : ""}
      <details ${listaVecinos.length < 25 ? "open" : ""}><summary>${listaVecinos.length} vecinos</summary>
        ${listaVecinos.map((v) => `<a href="#" data-nodo="${esc(v.id)}" class="chip" style="border-left:4px solid ${COLORES[v.tipo]};background:#2a2f3a;color:#dde;text-decoration:none">${esc(v.tipo === "pieza" || v.tipo === "hallazgo" || v.tipo === "pregunta" ? v.etiqueta : (v.ruta || v.etiqueta).split("/").pop())}</a>`).join("")}
      </details>
      <div class="md">${r.markdown != null ? md(r.markdown) : r.datos ? `<table>${Object.entries(r.datos).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</td></tr>`).join("")}</table>` : ""}</div>`
    lat.querySelectorAll("a[data-nodo]").forEach((a) => { a.onclick = (e) => { e.preventDefault(); selecciona(a.dataset.nodo) } })
    lat.querySelectorAll(".md a[href]").forEach((a) => {
      const href = a.getAttribute("href")
      if (!href || /^(https?:|#|mailto:)/.test(href) || !r.ruta) return
      const destino = decodeURIComponent(new URL(href, "http://x/" + r.ruta).pathname.slice(1))
      if (datos.nodos.some((x) => x.id === destino)) a.onclick = (e) => { e.preventDefault(); selecciona(destino) }
    })
  }
  const busca = document.getElementById("buscaNodo")
  busca.onkeydown = (e) => {
    if (e.key !== "Enter") return
    const t = busca.value.trim().toLowerCase()
    const n = g.graphData().nodes.find((x) => x.etiqueta.toLowerCase() === t || x.id.toLowerCase() === t)
      || g.graphData().nodes.find((x) => `${x.id} ${x.etiqueta}`.toLowerCase().includes(t))
    if (n) selecciona(n.id)
  }
  actualiza()
  const inicial = q.get("n")
  if (inicial) setTimeout(() => {
    const nodo = datos.nodos.find((x) => x.id === inicial)
    if (nodo && !activos.has(nodo.tipo)) { activos.add(nodo.tipo); actualiza() }
    selecciona(inicial)
  }, 1500)
}

/* ------------------------------------------------------------ esquema */

const FLUJO = `flowchart LR
  E[("Exemples<br>originales del cliente<br>OneDrive")] -->|inventariar.py| D[documento]
  E -->|extraer.py, lectores.py| C[elemento · celda · estructura]
  C -->|formulas_aleatorias.py| R[celda_aleatoria]
  C -->|lector_dr.py| L[lectura_dr · medida_dr]
  E -->|medidas_cmm.py| M[medida_cmm · medida_contorno]
  C -->|perfil_ppap.py| P[perfil_ppap]
  C -->|perfil_correcciones.py| PC[perfil_correccion]
  L & PC -->|cadena_correcciones.py| CC[cadena_correccion]
  E -->|globos_icp.py| G[globo]
  D -->|auditar_ingesta.py| A[auditoria · datos/aceptacion/*.jsonl]
  D & L & CC -. lectura humana y revisión .-> F["Fichas .md · incongruencias.md<br>hallazgos.jsonl · casos-referencia.jsonl"]
  F & D & L -->|rag.py construir| I[("datos/rag/indice.sqlite")]
  F -->|este visor| V{{Visor}}
  CC -->|este visor| V
  E -. los PDF de plano .-> V
  E -->|miniaturas_cad.py| MC[capturas de los STEP]
  MC --> V`

async function vistaEsquema() {
  const d = await una("/api/esquema")
  vista.innerHTML = `<section class="contenido">
    <h2>Esquema de lo que hay en conocimiento/</h2>
    <p>De dónde sale cada tabla y cómo se relacionan. La biblioteca se regenera desde los originales y <b>no es fuente de verdad</b>:
    las conclusiones revisadas viven en los Markdown y en <code>hallazgos.jsonl</code>. ${d.md} ficheros Markdown entran en el grafo.</p>
    <h3>Flujo</h3><div class="mermaid" id="flujo"></div>
    <h3>Tablas de la biblioteca y relaciones</h3>
    <p style="color:var(--suave)">Todas las tablas cuelgan de <code>documento</code> por <code>documento_id</code> (relación lógica; SQLite no la impone salvo en <code>elemento</code>/<code>celda</code>/<code>estructura</code>).
    <code>cadena_correccion</code> apunta a tres documentos: el PPTX de la corrección, el informe de origen y el de validación. La pieza y el muestreo <b>no son columnas</b> de <code>medida_dr</code>: se deducen de la carpeta (<code>documento.codigo</code>) y del nombre del fichero (<code>intern.NN</code>), y por eso se revisan en la pestaña Revisión.</p>
    <div class="mermaid" id="er"></div>
    <h3>Tamaño</h3>
    <table><tr><th>Tabla</th><th>Filas</th><th>Columnas</th></tr>
    ${d.tablas.map((t) => `<tr><td><code>${esc(t.nombre)}</code></td><td style="text-align:right">${num(t.filas)}</td><td style="font-size:11.5px">${t.columnas.map(esc).join(", ")}</td></tr>`).join("")}</table>
    <h3>Índice RAG (<code>datos/rag/indice.sqlite</code>)</h3>
    <table><tr><th>Tabla</th><th>Filas</th></tr>${d.rag.map((t) => `<tr><td><code>${esc(t.nombre)}</code></td><td>${num(t.filas)}</td></tr>`).join("")}</table>
    <h3>Registros en texto</h3>
    <table><tr><th>Fichero</th><th>Líneas</th><th>Tamaño</th></tr>${d.ficheros.map((f) => `<tr><td><code>${esc(f.ruta)}</code></td><td>${f.lineas ?? ""}</td><td>${num(Math.round(f.bytes / 1024))} KB</td></tr>`).join("")}</table>
  </section>`
  mermaid.initialize({ startOnLoad: false, theme: "default", er: { useMaxWidth: false }, flowchart: { useMaxWidth: true } })
  document.getElementById("flujo").innerHTML = (await mermaid.render("m-flujo", FLUJO)).svg
  document.getElementById("er").innerHTML = (await mermaid.render("m-er", d.er)).svg
}

/* ------------------------------------------------------------ revisión */

async function vistaRevision(recalcular = false) {
  vista.innerHTML = `<div class="vacio">${recalcular ? "Recalculando (tarda unos segundos)…" : "Cargando…"}</div>`
  const r = await api(`/api/revision${recalcular ? "?recalcular=true" : ""}`)
  const grupos = { pieza: "Pieza: ¿cada dato está en la pieza correcta?", muestreo: "Muestreo: ¿cada medida está en el muestreo correcto?" }
  vista.innerHTML = `<section class="contenido">
    <h2>Revisión de enlaces pieza y muestreo</h2>
    <p>Comprobaciones automáticas sobre la biblioteca y los JSONL (solo lectura). <span class="nivel aviso">aviso</span> = algo que mirar;
    <span class="nivel info">info</span> = esperado o ya documentado; <span class="nivel ok">ok</span> = sin casos.
    Resultado también en <code>prototypes/data-explorer/out/conocimiento/revision.md</code>. <button id="recalc">Recalcular</button></p>
    <div class="tarjetas">${Object.entries(r.resumen).map(([k, v]) => `<div class="cifra"><b class="nivel ${k}">${v}</b><span>${k}</span></div>`).join("")}</div>
    ${Object.entries(grupos).map(([g, titulo]) => `<h3>${titulo}</h3>` + r.comprobaciones.filter((x) => x.grupo === g).map((x) => `
      <details class="comp" ${x.nivel === "aviso" ? "" : ""}>
        <summary><span class="nivel ${x.nivel}">${x.nivel}</span><b>${esc(x.id)}</b> ${esc(x.titulo)}<span class="n">${num(x.n)}${x.total != null ? ` de ${num(x.total)}` : ""}</span></summary>
        <div class="cuerpo"><p>${esc(x.que)} ${x.nota ? `<i>${esc(x.nota)}</i>` : ""}</p>
        ${x.casos.length ? tabla(x.casos.slice(0, CASOS_VISIBLES)) + (x.n > CASOS_VISIBLES ? `<p style="color:var(--suave)">Se muestran ${CASOS_VISIBLES} de ${num(x.n)}; la lista completa está en <code>revision.json</code>.</p>` : "") : "<p>Sin casos.</p>"}
        </div></details>`).join("")).join("")}
  </section>`
  document.getElementById("recalc").onclick = () => vistaRevision(true)
}

function tabla(filas) {
  const claves = Object.keys(filas[0])
  return `<table><tr>${claves.map((k) => `<th>${esc(k)}</th>`).join("")}</tr>${filas.map((f) => `<tr>${claves.map((k) => `<td>${esc(f[k])}</td>`).join("")}</tr>`).join("")}</table>`
}

// Arranque al final: las variables de módulo (let) ya existen.
window.addEventListener("hashchange", render)
render()
