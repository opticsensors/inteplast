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
    else if (tab === "errores" && partes[1] === "generales") await vistaGenerales(q)
    else if (tab === "errores" && partes[1]) await vistaErroresPieza(partes[1], q)
    else if (tab === "errores") await vistaErrores()
  } catch (e) {
    vista.innerHTML = `<div class="vacio">Error: ${esc(e.message)}</div>`
    console.error(e)
  }
  // Las pestañas Planos y Piezas devuelven a su cuadrícula tal como se dejó (filtros y búsqueda).
  document.querySelector('header nav a[data-tab="planos"]').href = ultimaRejilla
  document.querySelector('header nav a[data-tab="piezas"]').href = ultimasPiezas
}

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

// Segundo tag, de contorno: si alguno de los números situados en el plano tiene datos en su ficha (medidas o correcciones).
const TAGS_DATOS = { con: { texto: "Cotas con datos", clase: "contorno verde" }, sin: { texto: "Cotas sin datos", clase: "contorno" } }

function tagDatos(p) {
  const t = TAGS_DATOS[p.datos]
  return t ? `<span class="chip ${t.clase}" title="${p.numeros_con_datos} de ${p.numeros} números situados en el plano tienen medidas o correcciones">${t.texto}</span>` : ""
}

async function vistaPlanos(q) {
  ultimaRejilla = location.hash || "#/planos"
  const { planos } = await una("/api/planos")
  const texto = q.get("q") || ""
  const feature = q.get("f") || ""
  const tag = q.get("t") || ""
  const conDatos = q.get("d") || ""
  const features = [...new Set(planos.map((p) => p.feature))].sort()
  vista.innerHTML = `
    <div class="barra">
      <input type="search" id="q" placeholder="Pieza, nombre, feature…" value="${esc(texto)}" style="width:320px">
      <select id="f"><option value="">Todos los features</option>${features.map((f) => `<option ${f === feature ? "selected" : ""}>${esc(f)}</option>`).join("")}</select>
      <select id="t"><option value="">Todos los tags</option>${Object.entries(TAGS).map(([k, v]) => `<option value="${k}" ${k === tag ? "selected" : ""}>${v.texto} (${planos.filter((p) => p.tag === k).length})</option>`).join("")}</select>
      <select id="d"><option value="">Con y sin datos</option>${Object.entries(TAGS_DATOS).map(([k, v]) => `<option value="${k}" ${k === conDatos ? "selected" : ""}>${v.texto} (${planos.filter((p) => p.datos === k).length})</option>`).join("")}</select>
    </div>
    <div class="rejilla" id="rejilla"></div>`
  const t = texto.toLowerCase()
  let lista = planos.filter((p) => (!feature || p.feature === feature) && (!tag || p.tag === tag) && (!conDatos || p.datos === conDatos))
  if (texto) lista = lista.filter((p) => `${p.codigo} ${p.nombre} ${p.feature} ${p.ruta}`.toLowerCase().includes(t))
  ordenPlanos = lista.map((p) => p.id)
  const rejilla = document.getElementById("rejilla")
  if (!lista.length) rejilla.innerHTML = `<div class="vacio">Ningún plano coincide.</div>`
  for (const p of lista) {
    const card = h(`<div class="tarjeta ${p.tag === "nada" ? "sin-busqueda" : ""}" title="${esc(p.ruta)}">
      <div class="mini"><img loading="lazy" alt="" src="${imagenPlano(p, 1, "mini")}"></div>
      <div class="pie"><b>${esc(p.codigo)}</b> · ${esc(p.feature)}
        <div class="nombre">${esc(p.nombre)}</div>
        ${tagPlano(p)}${tagDatos(p)}
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
    if (document.getElementById("d").value) p.set("d", document.getElementById("d").value)
    ir(`#/planos${p.toString() ? "?" + p : ""}`)
  }
  const qin = document.getElementById("q")
  qin.onkeydown = (e) => { if (e.key === "Enter") actualiza() }
  qin.focus(); qin.setSelectionRange(qin.value.length, qin.value.length)
  for (const id of ["f", "t", "d"]) document.getElementById(id).onchange = actualiza
}

/* ------------------------------------------------------------ planos: visor */

let marcarDatos = false // «Marcar cotas con datos»: siempre desactivada al abrir el visor

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
          <button id="ant" ${anterior ? "" : "disabled"}>◀</button>
          <button id="sig" ${siguiente ? "" : "disabled"}>▶</button>
          <b>${esc(p.codigo)}</b> <span style="color:var(--suave)">${esc(p.nombre)}</span> ${tagPlano(p)}${tagDatos(p)}
          <span style="margin-left:auto"></span>
          ${p.paginas > 1 ? `<select id="pag">${Array.from({ length: p.paginas }, (_, i) => `<option value="${i + 1}" ${i + 1 === pagina ? "selected" : ""}>página ${i + 1}</option>`).join("")}</select>` : ""}
          <button id="menos">−</button><button id="ajustar">Ajustar</button><button id="mas">+</button>
          <label><input type="checkbox" id="verGlobos" checked> globos</label>
        </div>
        <div class="visor" id="visor"><div class="lienzo" id="lienzo"><img id="img" alt=""><div class="capa" id="capa"></div></div></div>
      </div>
      <aside class="panel panel-plano">
        <input type="search" id="buscar" placeholder="Buscar: cota (N170) o texto" value="${esc(busqueda)}" style="width:100%">
        <div id="datosCotas" class="datos-cotas">
          <label title="En verde, los números del plano que tienen medidas (Excel o CSV) o correcciones en la pieza. Es el número de la pieza: el plano puede ser de otra revisión que los informes.">
            <input type="checkbox" id="verDatos" ${marcarDatos ? "checked" : ""}> Marcar cotas con datos</label>
          <span id="cuentaDatos" class="nota"></span>
        </div>
        <div id="estadoBusqueda" style="font-size:12px;color:var(--suave);margin:4px 0"></div>
        <ul class="resultados" id="resultados"></ul>
        <div id="cota"></div>
        ${p.local ? "" : `<div class="alerta">${esc(p.onedrive)}</div>`}
        <div id="avisoLectura" class="aviso-lectura" hidden>Lectura automática: puede fallar sin avisar.</div>
      </aside>
    </div>`
  const navega = (otro, extra = "") => ir(`#/planos/${otro}${extra}`)
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
  const conDatosPedido = api(`/api/plano/${id}/cotas-con-datos`)
  const g = await api(`/api/plano/${id}/${pagina}/globos`)
  // Solo cuando lo que se ve en el plano sale de leerlo (globos sin .icp o numeración): el .icp no se lee.
  const aviso = document.getElementById("avisoLectura")
  if (aviso) aviso.hidden = g.metodo !== "lectura"
  await listo
  const radio = Math.min(est.w, est.h) * 0.0085
  // En los planos limpios el globo no está dibujado: se reconstruye con su número y una línea hasta la cota.
  const sinDibujar = g.metodo === "aproximada" || g.metodo === "gemela"
  const claseGlobo = sinDibujar ? "aprox" : g.metodo === "lectura" ? "lectura" : ""
  const marcadores = []
  const numeros = [] // los globos o números del plano, con su etiqueta, para «Marcar cotas con datos»
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
    capa.append(d); marcadores.push(d); numeros.push({ d, etiqueta: b.etiqueta })
  }
  document.getElementById("verGlobos").onchange = (e) => marcadores.forEach((m) => { m.style.display = e.target.checked ? "" : "none" })

  // «Marcar cotas con datos»: en verde, los números de esta página cuya ficha tiene medidas o correcciones.
  // Igual en todos los planos, también «0 de 0». Desactivada al abrir el visor, para que se vea primero todo lo
  // que se detecta; se recuerda al pasar de un plano a otro.
  conDatosPedido.then((datosCotas) => {
    const cuenta = document.getElementById("cuentaDatos")
    if (!cuenta) return // se ha cambiado de pantalla
    const conjunto = new Set(datosCotas.cotas)
    const con = numeros.filter((x) => conjunto.has(x.etiqueta))
    cuenta.textContent = `${con.length} de ${numeros.length} cotas con datos`
    const ver = document.getElementById("verDatos")
    const pinta = () => con.forEach((x) => x.d.classList.toggle("con-datos", ver.checked))
    ver.onchange = () => { marcarDatos = ver.checked; pinta() }
    pinta()
  }).catch((e) => console.error(e))

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
    // La ficha es siempre la de lo buscado: con o sin medidas, nunca la de la cota anterior.
    if (r.cota && ES_COTA.test(texto)) mostrarCota(p.codigo, r.cota.cota, p.componente)
    else limpiaCota()
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

// Una búsqueda que es un número de cota (170, N170, No.170, []170, 45.1); lo demás es texto del plano.
const ES_COTA = /^(?:n|no\.?|\[\]|□)?\s*\d+(?:\.\d+)?$/i

function limpiaCota() {
  const div = document.getElementById("cota")
  if (!div) return
  div.dataset.pedido = String(+(div.dataset.pedido || 0) + 1) // descarta una ficha que aún estuviera cargando
  div.innerHTML = ""
}

const filaCota = (etiqueta, valor) => `<div class="fila-cota"><span>${etiqueta}</span><b>${valor}</b></div>`

// Lo que interesa de una cota al mirarla en el plano: si tiene medidas en los Excel y en los CSV, cuántas, y correcciones.
function resumenCota(r) {
  const info = r.info, dr = info.en_informes
  const excel = dr.medidas
    ? `${num(dr.medidas)} medidas en ${dr.documentos} informes${dr.excluidas ? ` <span class="nota" title="RAND, ceros y atípicos">(${num(dr.excluidas)} excluidas)</span>` : ""}`
    : info.pieza_con_medidas ? "sin medidas de esta cota" : "la pieza no tiene medidas leídas"
  const csv = info.csv == null ? "no leídos" : info.csv.medidas ? `${num(info.csv.medidas)} medidas en ${info.csv.ficheros} ficheros` : "sin medidas de esta cota"
  return filaCota("Excel (informes)", excel) + filaCota("CSV (CMM)", csv) +
    filaCota("Correcciones", r.correcciones.length ? cuantasCorrecciones(r.correcciones.length) : "ninguna")
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
    let r
    try {
      r = await api(`/api/pieza/${codigo}/cota?${consulta}`)
      // Un servidor arrancado antes de cambiar el código devuelve la ficha sin estos campos.
      if (!r.info || !r.info.en_informes || !("csv" in r.info)) throw new Error("el servidor del visor es de una versión anterior: reinícialo (app.py)")
    } catch (e) {
      if (div.isConnected && div.dataset.pedido === pedido) {
        div.innerHTML = `<div class="bloque"><b>Cota ${esc(cota)}</b><div class="alerta">No se ha podido cargar: ${esc(e.message)}</div></div>`
      }
      return
    }
    if (!div.isConnected || div.dataset.pedido !== pedido) return // se ha cambiado de pantalla o de globo mientras cargaba
    const titulo = `<b>Cota ${esc(cota)} · pieza ${esc(codigo)}${componente ? ` · ${esc(r.componentes.find((x) => x.id === componente)?.etiqueta)}` : ""}</b>`
    const botones = conjunto ? `<div class="selectores">${r.componentes.map((x) => `<button data-componente="${esc(x.id)}" class="${x.id === componente ? "activo" : ""}">${esc(x.etiqueta)} · ${num(x.valores)} valores</button>`).join("")}</div>` : ""
    if (conjunto && !componente) {
      div.innerHTML = `<div class="bloque">${titulo}<div class="nota">Este plano es el conjunto, y en cada pieza este número es otra cota. Elige cuál mirar:</div>${botones}</div>`
    } else {
      // La evolución está en la ficha de la pieza, con esta cota ya dibujada; solo se enlaza si hay algo que dibujar.
      const enlace = r.info.en_informes.medidas || r.info.csv?.medidas
        ? `<a href="#/piezas/${esc(codigo)}?c=${encodeURIComponent(cota)}${r.componente ? `&componente=${esc(r.componente)}` : ""}">Ver evolución completa →</a>` : ""
      div.innerHTML = `<div class="bloque">${titulo}${botones}${resumenCota(r)}${enlace}</div>`
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
  ["correcciones", "Pasos de corrección"], ["errores", "Errores propios pendientes"], ["generales", "Errores generales pendientes"]]
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

// Desglose de la columna «Ficheros»: se despliega bajo la fila al pulsarla. Sigue abierto al reordenar.
const desplegadasNumeros = new Set()
const AYUDA_TIPO = {
  "pdf": "PDF con capa de texto: se puede buscar en él.",
  "pdf escaneado": "PDF sin capa de texto: casi siempre un escaneo; alguno puede ser un PDF exportado como imagen. Para buscar en él haría falta OCR.",
  "vacíos": "Ficheros de 0 bytes o con solo saltos de línea. No cuentan en su tipo.",
  "otros sin texto extraíble": "Ficheros no PDF cuyo contenido no se puede consultar como texto; pueden contener imágenes o gráficos. Excluye los vacíos. No cuentan en su tipo (xls, docx…).",
}

async function desgloseFicheros(codigo) {
  const d = await una(`/api/pieza/${encodeURIComponent(codigo)}/ficheros`)
  // Una columna por tipo, de más a menos ficheros en la pieza, junto a «Ficheros», que es su suma. Vacía si no hay.
  const exts = d.total.tipos.map((t) => t.ext)
  const cifra = (n, clase = "") => `<td class="cifra-col ${clase} ${n ? "" : "cero"}">${num(n)}</td>`
  const tipo = (n) => n ? cifra(n, "tipo") : `<td class="tipo"></td>`
  const fila = (x, nombre, clase = "") => {
    const porTipo = Object.fromEntries(x.tipos.map((t) => [t.ext, t.n]))
    return `<tr class="${clase}"><td>${nombre}</td>${cifra(x.n)}${exts.map((e) => tipo(porTipo[e])).join("")}</tr>`
  }
  return `<div class="desglose-caja"><table class="desglose"><tr><th>Carpeta</th><th class="cifra-col">Ficheros</th>
    ${exts.map((e) => `<th class="cifra-col tipo" ${AYUDA_TIPO[e] ? `title="${esc(AYUDA_TIPO[e])}"` : ""}>${esc(e || "sin ext.")}</th>`).join("")}</tr>
    ${d.carpetas.map((x) => fila(x, esc(x.carpeta_norm ?? "—"))).join("")}${fila(d.total, "Total", "total")}</table></div>`
}

function despliegaFicheros(tr, ancho) {
  const codigo = tr.dataset.codigo
  if (tr.nextElementSibling?.classList.contains("detalle")) {
    tr.nextElementSibling.remove(); tr.classList.remove("abierta"); desplegadasNumeros.delete(codigo); return
  }
  desplegadasNumeros.add(codigo); tr.classList.add("abierta")
  const detalle = document.createElement("tr")
  detalle.className = "detalle"
  detalle.innerHTML = `<td colspan="${ancho}"><span class="nota">Cargando…</span></td>`
  tr.after(detalle)
  desgloseFicheros(codigo).then((html) => { detalle.firstElementChild.innerHTML = html })
    .catch((e) => { detalle.firstElementChild.textContent = `Error: ${e.message}` })
}

function tablaNumeros(cuerpo, lista, tags, familias) {
  const { campo, sentido } = ordenNumeros
  const orden = [...lista].sort((a, b) => sentido * (campo === "codigo" ? a.codigo.localeCompare(b.codigo) : a[campo] - b[campo]) || a.codigo.localeCompare(b.codigo))
  const titulo = (c, texto, clase = "") => `<th class="${clase}" data-campo="${c}" title="Ordenar">${texto}${c === campo ? (sentido > 0 ? " ▲" : " ▼") : ""}</th>`
  const ancho = 4 + CIFRAS.length
  cuerpo.innerHTML = `<div class="numeros"><p class="nota">Pulsa una fila para ver sus ficheros por carpeta; el número de la pieza abre su ficha.</p><table>
    <tr>${titulo("codigo", "Pieza")}<th class="fijo">Feature</th><th class="fijo">Tag</th><th class="fijo">Familia</th>${CIFRAS.map(([c, t]) => titulo(c, t, "cifra-col")).join("")}</tr>
    ${orden.map((p) => `<tr data-codigo="${esc(p.codigo)}"><td><a href="#/piezas/${esc(p.codigo)}" title="Abrir la ficha"><b>${esc(p.codigo)}</b></a></td><td>${esc(featuresDe(p).join(" | "))}</td><td>${tagPieza(p, tags)}</td><td>${familiaPieza(p, familias)}</td>${CIFRAS.map(([c]) => `<td class="cifra-col ${p[c] ? "" : "cero"}">${num(p[c])}</td>`).join("")}</tr>`).join("")}
  </table></div>`
  cuerpo.querySelectorAll("th[data-campo]").forEach((th) => {
    th.onclick = () => {
      const c = th.dataset.campo
      // La primera pulsación en una cifra pone arriba las piezas con más.
      ordenNumeros = c === campo ? { campo, sentido: -sentido } : { campo: c, sentido: c === "codigo" ? 1 : -1 }
      tablaNumeros(cuerpo, lista, tags, familias)
    }
  })
  cuerpo.querySelectorAll("tr[data-codigo]").forEach((tr) => {
    tr.onclick = (e) => { if (!e.target.closest("a")) despliegaFicheros(tr, ancho) }
    if (desplegadasNumeros.has(tr.dataset.codigo)) { desplegadasNumeros.delete(tr.dataset.codigo); despliegaFicheros(tr, ancho) }
  })
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
    <h2>Pieza ${esc(codigo)}</h2>
    <div>${tagPieza(d.resumen, tags)}${familiaPieza(d.resumen, familias)}${d.resumen.features.map((f) => `<span class="chip azul">${esc(f)}</span>`).join("")} ${d.resumen.carpetas.map((f) => `<span class="chip">${esc(f)}</span>`).join("")}</div>
    ${d.resumen.tag_motivo ? `<div class="nota">${esc(d.resumen.tag_motivo)}</div>` : ""}
    <div class="bloque" id="bloqueEvolucion">
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
    </div>`
  // Desde un plano («Ver evolución completa»): directamente a la gráfica de esa cota.
  if (q.get("c")) document.getElementById("bloqueEvolucion").scrollIntoView({ block: "start" })

  let componenteActual = null
  const cadenasActuales = () => d.cadenas.filter((x) => !componenteActual || !x.componente || x.componente === componenteActual)
  // Siempre todos los pasos, sin filtrar por la cota de la gráfica; pulsar una cota la dibuja.
  const tablaCad = () => {
    const filas = cadenasActuales()
    document.getElementById("filtroCad").textContent = `${filas.length} pasos`
    document.getElementById("tablaCad").innerHTML = `<tr><th>Cota</th><th>Corrección</th><th>Fecha</th><th>Origen</th><th>Validación</th><th>Estado</th><th>Avisos</th></tr>` +
      filas.map((x) => `<tr><td><a href="#" data-cota="${esc(x.cota)}">${esc(x.cota)}</a></td><td>${esc(x.numero ?? "")}</td><td>${esc(x.fecha_correccion ?? "")}</td>
        <td>${x.origen_muestreo != null ? `intern.${String(x.origen_muestreo).padStart(2, "0")} · ${x.origen_fuera ?? "?"}/${x.origen_n ?? "?"} fuera` : "—"}</td>
        <td>${x.validacion_muestreo != null ? `intern.${String(x.validacion_muestreo).padStart(2, "0")} · ${x.validacion_fuera ?? "?"}/${x.validacion_n ?? "?"} fuera` : "—"}</td>
        <td>${esc(x.validacion_estado ?? "")}</td><td style="font-size:11px;color:var(--suave)">${esc((JSON.parse(x.avisos || "[]") || []).join("; "))}</td></tr>`).join("")
    document.querySelectorAll("#tablaCad a[data-cota]").forEach((a) => { a.onclick = (e) => { e.preventDefault(); document.getElementById("selCota").value = a.dataset.cota; dibuja() } })
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
    tablaCad()
  }
  const muestraCota = evolucionCota(document.getElementById("evolucion"), codigo, { componente: q.get("componente"), alCargar })
  const dibuja = () => {
    const cota = document.getElementById("selCota").value
    if (cota) muestraCota(cota)
    else { document.getElementById("evolucion").innerHTML = `<div class="vacio">Sin medidas DR.</div>`; tablaCad() }
  }
  document.getElementById("selCota").onchange = dibuja
  dibuja()
}

/* ------------------------------------------------------------ errores */

// Ninguna incidencia se presenta como error demostrado: «Pendiente de aclarar» es lo que falta aclarar con INTEPLAST.
const CLASE_ESTADO = { "Duda": "morado", "Pendiente de aclarar": "naranja", "Explicación posible · sin confirmar": "azul", "Resuelta": "verde", "Corregida": "verde" }

function resumenTexto(t, largo = 320) {
  t = t || ""
  if (t.length <= largo) return { corto: t, cortado: false }
  const corte = t.lastIndexOf(" ", largo - 10)
  return { corto: t.slice(0, corte > largo / 2 ? corte : largo) + "…", cortado: true }
}

function piezasDeIncidencia(i, actual, catalogo) {
  const enlace = (c) => catalogo.has(c) ? `<a href="#/errores/${esc(c)}">${esc(c)}</a>` : `${esc(c)} (fuera del catálogo)`
  if (!i.piezas.length) return `<div class="nota">No cita ninguna pieza.</div>`
  const otras = i.piezas.filter((c) => c !== actual)
  if (!otras.length) return ""
  return `<div class="nota">${actual ? "También afecta a" : `Afecta a ${i.piezas.length > 1 ? `${i.piezas.length} piezas:` : ""}`} ${otras.map(enlace).join(", ")}</div>`
}

function tarjetaIncidencia(i, actual, catalogo) {
  const { corto, cortado } = resumenTexto(i.texto)
  const detalle = cortado || i.evidencia.length || i.graficas.length
  return `<div class="incidencia ${i.pendiente ? "" : "cerrada"}">
    <div class="cab"><span class="chip ${CLASE_ESTADO[i.estado] || ""}">${esc(i.estado)}</span><b>${esc(i.titulo)}</b><span class="id">${esc(i.id)}</span></div>
    <p>${esc(corto)}</p>
    ${piezasDeIncidencia(i, actual, catalogo)}
    ${detalle ? `<details><summary>Ver evidencia</summary>
      ${cortado ? `<p>${esc(i.texto)}</p>` : ""}
      ${i.evidencia.length ? `<ul class="evidencia">${i.evidencia.map((e) => `<li><b>${esc(e.fichero)}</b>${e.localizador ? ` · ${esc(e.localizador)}` : ""}<div class="nota">${esc(e.carpeta)}</div></li>`).join("")}</ul>` : ""}
      ${i.graficas.map((g) => `<p><a href="#/piezas/${esc(g.pieza)}?c=${encodeURIComponent(g.cota)}">Ver la gráfica de la cota ${esc(g.cota)} de la ${esc(g.pieza)} →</a></p>`).join("")}
    </details>` : ""}
  </div>`
}

// Pendientes por defecto, también las de explicación posible (sin confirmar); las resueltas y corregidas, con la casilla.
function listaIncidencias(incidencias, q, actual, catalogo, vacio) {
  const todas = q.get("todas") === "1"
  const cerradas = incidencias.filter((i) => !i.pendiente).length
  const lista = todas ? incidencias : incidencias.filter((i) => i.pendiente)
  return `${cerradas ? `<label class="nota"><input type="checkbox" id="todas" ${todas ? "checked" : ""}> Mostrar también las resueltas y corregidas (${cerradas})</label>` : ""}
    ${lista.length ? lista.map((i) => tarjetaIncidencia(i, actual, catalogo)).join("") : `<div class="vacio">${incidencias.length ? "Ninguna pendiente." : vacio}</div>`}`
}

function casillaTodas(q) {
  const casilla = document.getElementById("todas")
  if (!casilla) return
  casilla.onchange = () => {
    const p = new URLSearchParams(q)
    if (casilla.checked) p.set("todas", "1"); else p.delete("todas")
    const [camino] = location.hash.split("?")
    ir(`${camino}${p.toString() ? "?" + p : ""}`)
  }
}

const catalogoPiezas = async () => new Set((await una("/api/piezas")).piezas.map((p) => p.codigo))

function contadorErrores(e) {
  const propias = e.propias ? `<b>${e.propias_pendientes}</b> propia${e.propias_pendientes === 1 ? "" : "s"} pendiente${e.propias_pendientes === 1 ? "" : "s"} de ${e.propias}` : "Sin incidencias propias"
  const generales = e.generales ? ` · <b>${e.generales_pendientes}</b> general${e.generales_pendientes === 1 ? "" : "es"}` : ""
  return propias + generales
}

async function vistaErrores() {
  const { piezas, otras } = await api("/api/errores")
  vista.innerHTML = `<section class="contenido">
    <h2>Errores</h2>
    <p class="nota">Incongruencias y dudas de los datos, por pieza. «Pendiente de aclarar» no quiere decir comprobado: es lo que falta
    aclarar con INTEPLAST. «Explicación posible» es una hipótesis sin confirmar y también cuenta como pendiente. Las generales afectan a varias piezas y tienen una sola ficha; cada pieza cuenta las que le afectan.</p>
    <div class="filas-errores">
      ${piezas.map((p) => `<a class="fila-error" href="#/errores/${esc(p.codigo)}">
        <div class="mini"><img loading="lazy" alt="" src="/cad/${esc(p.codigo)}.jpg"></div>
        <div class="que"><b>${esc(p.codigo)}</b> <span class="nota">${esc([...new Set(p.carpetas)].join(" · "))}</span>
          <div>${[...new Set(p.features)].map((f) => `<span class="chip">${esc(f)}</span>`).join("")}</div></div>
        <div class="contador ${p.propias_pendientes || p.generales_pendientes ? "pendiente" : ""}">${contadorErrores(p)}</div></a>`).join("")}
      <a class="fila-error" href="#/errores/generales">
        <div class="mini">∑</div>
        <div class="que"><b>Generales y otras referencias</b><div class="nota">Afectan a varias piezas, no citan ninguna o son de una pieza fuera del catálogo</div></div>
        <div class="contador ${otras.pendientes ? "pendiente" : ""}"><b>${otras.pendientes}</b> pendiente${otras.pendientes === 1 ? "" : "s"} de ${otras.total}</div></a>
    </div></section>`
  vista.querySelectorAll(".fila-error img").forEach((img) => { img.onerror = () => { img.replaceWith(h(`<span>sin miniatura</span>`)) } })
}

async function vistaErroresPieza(codigo, q) {
  const [d, catalogo] = await Promise.all([api(`/api/errores/pieza/${encodeURIComponent(codigo)}`), catalogoPiezas()])
  vista.innerHTML = `<section class="contenido">
    <p><button id="volver" title="Volver a la lista de piezas">☰ Lista</button></p>
    <h2>Errores · pieza ${esc(codigo)}</h2>
    ${d.generales ? `<p><a href="#/errores/generales?pieza=${esc(codigo)}">Le afectan además ${d.generales} incidencia${d.generales === 1 ? "" : "s"} general${d.generales === 1 ? "" : "es"} (${d.generales_pendientes} pendiente${d.generales_pendientes === 1 ? "" : "s"}) →</a></p>` : ""}
    ${listaIncidencias(d.incidencias, q, codigo, catalogo, "Esta pieza no tiene incidencias propias.")}
  </section>`
  document.getElementById("volver").onclick = () => ir("#/errores")
  casillaTodas(q)
}

async function vistaGenerales(q) {
  const pieza = q.get("pieza")
  const [d, catalogo] = await Promise.all([api(`/api/errores/generales${pieza ? `?pieza=${encodeURIComponent(pieza)}` : ""}`), catalogoPiezas()])
  vista.innerHTML = `<section class="contenido">
    <p><button id="volver" title="Volver a la lista de piezas">☰ Lista</button></p>
    <h2>${pieza ? `Incidencias generales que afectan a la ${esc(pieza)}` : "Generales y otras referencias"}</h2>
    <p class="nota">${pieza ? `Solo las generales que citan la ${esc(pieza)}. <a href="#/errores/${esc(pieza)}">Errores propios de la ${esc(pieza)} →</a> · <a href="#/errores/generales">todas las generales →</a>`
      : "Las de la sección «Transversales» de las incongruencias, más las que no citan ninguna pieza del catálogo."}</p>
    ${listaIncidencias(d.incidencias, q, pieza, catalogo, "No le afecta ninguna incidencia general.")}
  </section>`
  document.getElementById("volver").onclick = () => ir(pieza ? `#/errores/${pieza}` : "#/errores")
  casillaTodas(q)
}

// Arranque al final: las variables de módulo (let) ya existen.
window.addEventListener("hashchange", render)
render()
