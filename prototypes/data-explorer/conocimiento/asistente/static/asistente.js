/* Pestaña «Asistente»: chat con Claude Haiku 5.5 sobre conocimiento/ y docs/ (ver asistente/README.md).
   Autocontenido: no usa nada de app.js. Se registra en window.vistasExtra.asistente y añade su enlace al menú;
   en otra página basta con montarAsistente(contenedor). */
"use strict"
;(() => {
  const API = "/api/asistente"
  const MODELO = "Claude Haiku 5.5"
  const EJEMPLOS = [
    "¿Qué warnings y lessons learned hay del Bolt Eye en la pieza 3212?",
    "¿Qué pasó con la cota N170 del 3212 tras las correcciones de molde?",
    "¿En qué se parecen y en qué se diferencian los features de Exemples?",
    "¿Qué incongruencias de los datos siguen pendientes de aclarar con INTEPLAST?",
  ]

  const css = document.createElement("link")
  css.rel = "stylesheet"
  css.href = "/asistente/asistente.css"
  document.head.append(css)

  // mensajes: {rol: "usuario", texto} | {rol: "asistente", partes: [...], fin, error, inicio, parada, pasosCerrados}
  const estado = { mensajes: [], ocupado: false, preparado: false }
  let raiz = null

  /* ---------------------------------------------------------------- markdown (subconjunto, siempre escapado) */

  const escapar = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c])

  function enLinea(s) { // s ya escapado
    const codigos = []
    s = s.replace(/`([^`]+)`/g, (_, c) => { codigos.push(c); return `\u0000${codigos.length - 1}\u0000` })
    s = s.replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/(^|[\s(])\*([^*\s][^*]*?)\*(?=[\s).,;:]|$)/g, "$1<i>$2</i>")
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => /^https?:\/\//.test(u)
      ? `<a href="${u}" target="_blank" rel="noopener">${t}</a>` : `${t} <code>${u}</code>`)
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codigos[+i]}</code>`)
  }

  const ES_LISTA = /^\s*([-*+]|\d+[.)])\s+/
  const ES_TABLA = /^\s*\|.*\|\s*$/
  const celdas = (f) => f.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim())
  const esSeparador = (f) => celdas(f).every((c) => /^:?-{2,}:?$/.test(c))

  function tabla(filas) {
    let cabecera = null
    if (filas.length > 1 && esSeparador(filas[1])) { cabecera = celdas(filas[0]); filas = filas.slice(2) }
    return `<div class="as-tabla"><table>${cabecera ? `<thead><tr>${cabecera.map((c) => `<th>${enLinea(c)}</th>`).join("")}</tr></thead>` : ""}
      <tbody>${filas.filter((f) => !esSeparador(f)).map((f) => `<tr>${celdas(f).map((c) => `<td>${enLinea(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
  }

  function markdown(md) {
    const l = escapar(md).replace(/\r/g, "").split("\n")
    const out = []
    let i = 0
    while (i < l.length) {
      if (/^\s*```/.test(l[i])) {
        const b = []
        for (i++; i < l.length && !/^\s*```/.test(l[i]); i++) b.push(l[i])
        i++
        out.push(`<pre><code>${b.join("\n")}</code></pre>`)
      } else if (ES_TABLA.test(l[i])) {
        const f = []
        while (i < l.length && ES_TABLA.test(l[i])) f.push(l[i++])
        out.push(tabla(f))
      } else if (ES_LISTA.test(l[i])) {
        const ordenada = /^\s*\d/.test(l[i])
        const items = []
        while (i < l.length && (ES_LISTA.test(l[i]) || (/^\s{2,}\S/.test(l[i]) && items.length))) {
          if (ES_LISTA.test(l[i])) items.push(l[i].replace(ES_LISTA, ""))
          else items[items.length - 1] += " " + l[i].trim()
          i++
        }
        const t = ordenada ? "ol" : "ul"
        out.push(`<${t}>${items.map((x) => `<li>${enLinea(x)}</li>`).join("")}</${t}>`)
      } else if (/^#{1,6}\s/.test(l[i])) {
        out.push(`<h4>${enLinea(l[i++].replace(/^#+\s+/, ""))}</h4>`)
      } else if (/^\s*(-{3,}|\*{3,})\s*$/.test(l[i])) {
        out.push("<hr>"); i++
      } else if (!l[i].trim()) {
        i++
      } else {
        const b = [l[i++]]
        while (i < l.length && l[i].trim() && !/^\s*```|^#{1,6}\s/.test(l[i]) && !ES_TABLA.test(l[i]) && !ES_LISTA.test(l[i])) b.push(l[i++])
        out.push(`<p>${enLinea(b.join("<br>"))}</p>`)
      }
    }
    return out.join("")
  }

  /* ---------------------------------------------------------------- pintar */

  const seg = (s) => `${Number(s).toLocaleString("es-ES", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} s`

  function trozos(m) {
    // Lo escrito antes del último paso es una nota de trabajo; lo de después, la respuesta.
    let ultimo = -1
    m.partes.forEach((p, i) => { if (p.tipo !== "texto") ultimo = i })
    const notas = m.partes.slice(0, ultimo + 1).filter((p) => p.tipo !== "texto" || p.texto.trim())
    const final = m.partes.slice(ultimo + 1).map((p) => p.texto).join("")
    return { notas, respuesta: m.fin?.respuesta || final }
  }

  function htmlPaso(p) {
    if (p.tipo === "texto") return `<li class="as-nota">${escapar(p.texto.trim())}</li>`
    if (p.tipo === "aviso") return `<li class="as-aviso">${escapar(p.texto)}</li>`
    const icono = { curso: '<span class="as-girando"></span>', ok: "✓", error: "✕" }[p.estado]
    const tiempo = p.segundos != null ? `<span class="as-t">${seg(p.segundos)}</span>` : ""
    const detalle = p.detalle ? `<div class="as-detalle">${escapar(p.detalle)}</div>` : ""
    return `<li class="as-paso ${p.estado}"><span class="as-icono">${icono}</span><span>${escapar(p.texto)}${detalle}</span>${tiempo}</li>`
  }

  function htmlAsistente(m, i, enCurso) {
    const { notas, respuesta } = trozos(m)
    const pasos = notas.filter((p) => p.tipo === "paso").length
    const lista = notas.length ? `<details class="as-pasos" data-i="${i}" ${m.pasosCerrados ? "" : "open"}>
        <summary>${pasos} paso${pasos === 1 ? "" : "s"}: búsquedas y lecturas</summary><ol>${notas.map(htmlPaso).join("")}</ol></details>` : ""
    const pensando = enCurso && !respuesta && !notas.some((p) => p.estado === "curso")
      ? `<div class="as-pensando"><span class="as-girando"></span> Pensando…</div>` : ""
    const error = m.parada ? `<div class="as-error">Parada.</div>` : m.error ? `<div class="as-error">${escapar(m.error)}</div>` : ""
    const pie = m.fin ? `${seg(m.fin.segundos)} · ${pasos} paso${pasos === 1 ? "" : "s"} · ${MODELO}`
      : enCurso ? `<span class="as-crono">${seg((performance.now() - m.inicio) / 1000)}</span> · ${MODELO}` : ""
    return `<div class="as-msg as-asistente">${lista}${pensando}<div class="as-respuesta">${markdown(respuesta)}</div>${error}
      ${pie ? `<div class="as-pie">${pie}</div>` : ""}</div>`
  }

  function pintar() {
    if (!raiz?.isConnected) return
    const lista = raiz.querySelector(".as-mensajes")
    const abajo = lista.scrollHeight - lista.scrollTop - lista.clientHeight < 80
    const ultimo = estado.mensajes.length - 1
    lista.innerHTML = estado.mensajes.length
      ? estado.mensajes.map((m, i) => m.rol === "usuario"
        ? `<div class="as-msg as-usuario">${escapar(m.texto)}</div>`
        : htmlAsistente(m, i, estado.ocupado && i === ultimo)).join("")
      : `<div class="as-vacio"><p>Pregunta lo que quieras sobre las piezas, features, cotas, correcciones de molde, incidencias o la
          aplicación. Responde solo con <code>conocimiento/</code> y <code>docs/</code>, y cita de dónde sale cada dato.</p>
          <div class="as-ejemplos">${EJEMPLOS.map((e) => `<button type="button" class="as-ejemplo">${escapar(e)}</button>`).join("")}</div></div>`
    lista.querySelectorAll(".as-ejemplo").forEach((b) => { b.onclick = () => enviar(b.textContent) })
    lista.querySelectorAll(".as-pasos").forEach((d) => {
      d.ontoggle = () => { estado.mensajes[+d.dataset.i].pasosCerrados = !d.open }
    })
    if (abajo) lista.scrollTop = lista.scrollHeight
    raiz.querySelector(".as-enviar").disabled = estado.ocupado
    raiz.querySelector(".as-parar").hidden = !estado.ocupado
    raiz.querySelector(".as-nueva").disabled = estado.ocupado || !estado.mensajes.length
  }

  setInterval(() => {
    const c = raiz?.isConnected && estado.ocupado && raiz.querySelector(".as-crono")
    if (c) c.textContent = seg((performance.now() - estado.mensajes[estado.mensajes.length - 1].inicio) / 1000)
  }, 100)

  /* ---------------------------------------------------------------- conversación */

  function aplicar(m, e) {
    const ultima = m.partes[m.partes.length - 1]
    if (e.tipo === "texto_nuevo") m.partes.push({ tipo: "texto", texto: "" })
    else if (e.tipo === "texto") {
      if (ultima?.tipo === "texto") ultima.texto += e.texto
      else m.partes.push({ tipo: "texto", texto: e.texto })
    } else if (e.tipo === "paso") m.partes.push({ tipo: "paso", id: e.id, texto: e.texto, estado: "curso" })
    else if (e.tipo === "resultado_paso") {
      const p = m.partes.find((x) => x.id === e.id)
      if (p) Object.assign(p, { estado: e.error ? "error" : "ok", segundos: e.segundos, detalle: e.detalle })
    } else if (e.tipo === "aviso") m.partes.push({ tipo: "aviso", texto: e.texto })
    else if (e.tipo === "fin") m.fin = e
    else if (e.tipo === "error") m.error = e.texto + (e.detalle ? `\n${e.detalle}` : "")
  }

  async function enviar(texto) {
    texto = texto.trim()
    if (!texto || estado.ocupado) return
    const m = { rol: "asistente", partes: [], fin: null, error: null, inicio: performance.now() }
    estado.mensajes.push({ rol: "usuario", texto }, m)
    estado.ocupado = true
    pintar()
    raiz?.querySelector(".as-mensajes")?.scrollTo(0, 1e9)
    try {
      const r = await fetch(`${API}/preguntar`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ texto }) })
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Error ${r.status}`)
      const lector = r.body.getReader()
      const dec = new TextDecoder()
      let resto = ""
      for (;;) {
        const { value, done } = await lector.read()
        if (done) break
        resto += dec.decode(value, { stream: true })
        const lineas = resto.split("\n")
        resto = lineas.pop()
        for (const l of lineas) if (l.trim()) aplicar(m, JSON.parse(l))
        pintar()
      }
    } catch (e) {
      m.error = e.message || String(e)
    }
    if (!m.fin && !m.error && !m.parada) m.error = "La respuesta se ha cortado."
    m.partes.forEach((p) => { if (p.estado === "curso") p.estado = "error" })
    estado.ocupado = false
    pintar()
    raiz?.querySelector(".as-texto")?.focus()
  }

  async function parar() {
    const m = estado.mensajes[estado.mensajes.length - 1]
    if (m) m.parada = true
    await fetch(`${API}/parar`, { method: "POST" })
  }

  async function nueva() {
    if (estado.ocupado) return
    await fetch(`${API}/nueva`, { method: "POST" })
    estado.mensajes = []
    estado.preparado = false
    preparar()
    pintar()
  }

  function preparar() {
    if (estado.preparado) return
    estado.preparado = true
    fetch(`${API}/preparar`, { method: "POST" }).then(async (r) => {
      if (!r.ok) {
        estado.preparado = false
        const aviso = raiz?.querySelector(".as-estado")
        if (aviso) aviso.textContent = (await r.json().catch(() => ({}))).detail || `No se puede arrancar Claude (${r.status})`
      }
    })
  }

  /* ---------------------------------------------------------------- montar */

  function montar(contenedor) {
    contenedor.innerHTML = `<section class="as-vista">
      <div class="as-cabecera">
        <div><h2>Asistente</h2><p class="as-sub as-estado"></p></div>
        <div class="as-botones"><button type="button" class="as-parar" hidden>■ Parar</button>
          <button type="button" class="as-nueva" title="Olvida la conversación y empieza otra">Nueva conversación</button></div>
      </div>
      <div class="as-mensajes"></div>
      <form class="as-entrada">
        <textarea class="as-texto" rows="2" placeholder="Escribe tu pregunta… (Intro para enviar, Mayús+Intro para salto de línea)"></textarea>
        <button type="submit" class="as-enviar">Enviar</button>
      </form>
    </section>`
    raiz = contenedor.querySelector(".as-vista")
    const area = raiz.querySelector(".as-texto")
    raiz.querySelector(".as-entrada").onsubmit = (ev) => {
      ev.preventDefault()
      const t = area.value
      if (t.trim() && !estado.ocupado) { area.value = ""; enviar(t) }
    }
    area.onkeydown = (ev) => {
      if (ev.key === "Enter" && !ev.shiftKey && !ev.isComposing) { ev.preventDefault(); raiz.querySelector(".as-entrada").requestSubmit() }
    }
    raiz.querySelector(".as-parar").onclick = parar
    raiz.querySelector(".as-nueva").onclick = nueva
    pintar()
    raiz.querySelector(".as-mensajes").scrollTop = 1e9
    area.focus()
    preparar()
  }

  window.montarAsistente = montar
  window.vistasExtra = Object.assign(window.vistasExtra || {}, { asistente: (contenedor) => montar(contenedor) })
  const menu = document.querySelector("header nav")
  if (menu && !menu.querySelector('[data-tab="asistente"]')) menu.insertAdjacentHTML("beforeend", '<a href="#/asistente" data-tab="asistente">Asistente</a>')
})()
