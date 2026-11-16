"""Una conversación viva con Claude Code (`claude -p` en stream-json), reutilizable fuera del visor.

Un solo proceso por conversación: se arranca una vez y cada pregunta se le escribe por la entrada, así que recuerda lo
anterior y no paga el arranque en cada pregunta. Usa la sesión de Claude Code de quien lo ejecuta (su suscripción):
**solo para uso personal en su equipo**, no para ofrecerlo a otros.

Encierro (comprobado el 12/11/2026 con Claude Code 2.1.322):
- `--restricted`: las herramientas de ficheros solo ven `conocimiento/` (directorio de trabajo) y `docs/` (`--add-dir`);
  no carga los ajustes del usuario ni del proyecto.
- `--tools Read,Grep,Glob`: sin Bash, PowerShell ni edición. El resto de la biblioteca llega por el servidor MCP propio
  (`herramientas_mcp.py`), de solo lectura.
- `--permission-prompts none`: lo que pediría permiso se deniega solo.
- `--safe-mode` no se usa porque desactiva también el MCP; CLAUDE.md y la memoria se apagan por variables de entorno.

    s = SesionClaude()
    for evento in s.preguntar("¿Qué warnings tiene el Bolt Eye?"):
        print(evento)            # {"tipo": "paso" | "texto" | "resultado_paso" | "fin" | "error" | "aviso", ...}
    s.cerrar()
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[3]
SERVIDOR_MCP = "conocimiento"
PLAZO_EVENTO = 300  # s sin ningún evento de Claude antes de darlo por colgado


def _claude() -> str:
    candidatos = [shutil.which("claude"), str(Path.home() / ".local" / "bin" / ("claude.exe" if os.name == "nt" else "claude"))]
    for c in candidatos:
        if c and Path(c).is_file():
            return c
    raise FileNotFoundError("No encuentro el ejecutable de Claude Code (claude). ¿Está instalado y con sesión iniciada?")


@dataclass
class Config:
    modelo: str = "claude-haiku-5-5"
    cwd: Path = REPO / "conocimiento"
    otras_carpetas: tuple[Path, ...] = (REPO / "docs",)
    herramientas: str = "Read,Grep,Glob"
    instrucciones: Path = AQUI / "instrucciones.md"
    python_mcp: Path = REPO / "conocimiento" / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    servidor_mcp: Path = AQUI / "herramientas_mcp.py"
    entorno: dict = field(default_factory=lambda: {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
                                                   "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})


class Ocupada(RuntimeError):
    """Ya hay una pregunta en curso: una a la vez."""


class SesionClaude:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self._proc: subprocess.Popen | None = None
        self._eventos: queue.Queue | None = None
        self._cerrojo = threading.Lock()
        self._stderr: deque[str] = deque(maxlen=40)
        self.id_sesion: str | None = None   # para reanudar la misma conversación si el proceso se cae
        self.turnos = 0

    # ------------------------------------------------------------------ proceso

    def _comando(self) -> list[str]:
        c = self.config
        mcp = {"mcpServers": {SERVIDOR_MCP: {"type": "stdio", "command": str(c.python_mcp), "args": ["-u", str(c.servidor_mcp)]}}}
        cmd = [_claude(), "-p", "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
               "--include-partial-messages", "--model", c.modelo,
               "--restricted", "--tools", c.herramientas, "--permission-prompts", "none",
               "--strict-mcp-config", "--mcp-config", json.dumps(mcp),
               "--allowedTools", f"mcp__{SERVIDOR_MCP}",
               "--append-system-prompt-file", str(c.instrucciones)]
        for d in c.otras_carpetas:
            cmd += ["--add-dir", str(d)]
        if self.id_sesion:
            cmd += ["--resume", self.id_sesion]
        return cmd

    def vivo(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def preparar(self) -> None:
        """Arranca el proceso (y el servidor MCP, que se calienta solo) sin gastar nada: aún no se pregunta."""
        if self.vivo():
            return
        eventos: queue.Queue = queue.Queue()
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self._proc = proc = subprocess.Popen(
            self._comando(), cwd=self.config.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, **self.config.entorno}, creationflags=flags)
        self._eventos = eventos

        def leer() -> None:
            for linea in proc.stdout:
                try:
                    eventos.put(json.loads(linea.decode("utf-8", "replace")))
                except json.JSONDecodeError:
                    self._stderr.append(linea.decode("utf-8", "replace").rstrip())
            eventos.put(None)

        def leer_errores() -> None:
            for linea in proc.stderr:
                self._stderr.append(linea.decode("utf-8", "replace").rstrip())

        threading.Thread(target=leer, daemon=True).start()
        threading.Thread(target=leer_errores, daemon=True).start()

    def parar(self) -> None:
        """Corta la respuesta en curso. La conversación sigue: la próxima pregunta la reanuda (`--resume`)."""
        proc, self._proc = self._proc, None
        if proc is None or proc.poll() is not None:
            return
        if os.name == "nt":  # también el servidor MCP y lo que cuelgue de él
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            proc.kill()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass

    def nueva(self) -> None:
        """Olvida la conversación: la próxima pregunta empieza de cero."""
        self.parar()
        self.id_sesion, self.turnos = None, 0

    cerrar = parar

    def estado(self) -> dict:
        return {"vivo": self.vivo(), "ocupada": self._cerrojo.locked(), "sesion": self.id_sesion, "turnos": self.turnos,
                "modelo": self.config.modelo}

    @property
    def ocupada(self) -> bool:
        return self._cerrojo.locked()

    # ------------------------------------------------------------------ preguntas

    def preguntar(self, texto: str) -> Iterator[dict]:
        if not self._cerrojo.acquire(blocking=False):
            raise Ocupada("Ya hay una pregunta en curso")
        terminado = False
        try:
            self.preparar()
            eventos, proc = self._eventos, self._proc
            mensaje = {"type": "user", "message": {"role": "user", "content": texto}, "parent_tool_use_id": None}
            try:
                proc.stdin.write(json.dumps(mensaje, ensure_ascii=False).encode("utf-8") + b"\n")
                proc.stdin.flush()
            except OSError:
                yield {"tipo": "error", "texto": "El proceso de Claude no acepta la pregunta.", "detalle": self._ultimos_errores()}
                self.parar()
                return
            traductor = Traductor(self.config.cwd)
            while True:
                try:
                    e = eventos.get(timeout=PLAZO_EVENTO)
                except queue.Empty:
                    yield {"tipo": "error", "texto": f"Claude no responde desde hace {PLAZO_EVENTO} s; se corta la respuesta."}
                    self.parar()
                    return
                if e is None:
                    if self._proc is proc:  # no lo hemos parado nosotros
                        yield {"tipo": "error", "texto": "El proceso de Claude se ha cerrado.", "detalle": self._ultimos_errores()}
                        self._proc = None
                    return
                if e.get("session_id"):
                    self.id_sesion = e["session_id"]
                yield from traductor(e)
                if e.get("type") == "result":
                    self.turnos += 1
                    terminado = True
                    return
        finally:
            if not terminado and self.vivo():
                self.parar()  # respuesta a medias (p. ej. el navegador cortó): no dejar eventos colgando
            self._cerrojo.release()

    def _ultimos_errores(self) -> str:
        return "\n".join(list(self._stderr)[-8:])


class Traductor:
    """De los eventos de stream-json a otros más simples para la interfaz."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd
        self.t0 = time.monotonic()
        self.pasos: dict[str, float] = {}

    def __call__(self, e: dict) -> Iterator[dict]:
        tipo = e.get("type")
        if tipo == "stream_event":
            ev = e.get("event") or {}
            if ev.get("type") == "content_block_start" and (ev.get("content_block") or {}).get("type") == "text":
                yield {"tipo": "texto_nuevo"}
            elif ev.get("type") == "content_block_delta" and (ev.get("delta") or {}).get("type") == "text_delta":
                yield {"tipo": "texto", "texto": ev["delta"]["text"]}
        elif tipo == "assistant":
            for b in (e.get("message") or {}).get("content", []):
                if b.get("type") == "tool_use":
                    self.pasos[b["id"]] = time.monotonic()
                    yield {"tipo": "paso", "id": b["id"], "texto": self.describir(b["name"], b.get("input") or {})}
        elif tipo == "user":
            contenido = (e.get("message") or {}).get("content")
            for b in contenido if isinstance(contenido, list) else []:
                if b.get("type") == "tool_result":
                    inicio = self.pasos.get(b.get("tool_use_id"), time.monotonic())
                    salida = {"tipo": "resultado_paso", "id": b.get("tool_use_id"), "error": bool(b.get("is_error")),
                              "segundos": round(time.monotonic() - inicio, 1)}
                    if salida["error"]:
                        c = b.get("content")
                        c = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                        salida["detalle"] = c.replace(str(REPO), "…")[:300]
                    yield salida
        elif tipo == "system" and e.get("subtype") == "api_retry":
            yield {"tipo": "aviso", "texto": f"Reintentando la llamada al modelo ({e.get('attempt')}/{e.get('max_retries')})…"}
        elif tipo == "result":
            yield {"tipo": "fin", "respuesta": e.get("result") or "", "error": bool(e.get("is_error")),
                   "subtipo": e.get("subtype"), "segundos": round(time.monotonic() - self.t0, 1),
                   "llamadas_modelo": e.get("num_turns")}

    def _rel(self, ruta: str | None) -> str:
        if not ruta:
            return "conocimiento/"
        p = Path(ruta)
        if not p.is_absolute():
            p = self.cwd / p
        try:
            return p.resolve().relative_to(REPO).as_posix()
        except ValueError:
            return ruta

    def describir(self, nombre: str, a: dict) -> str:
        filtros = " · ".join(f"{k} {a[k]}" for k in ("pieza", "feature", "cota") if a.get(k))
        filtros = f" ({filtros})" if filtros else ""
        corto = nombre.removeprefix(f"mcp__{SERVIDOR_MCP}__")
        # medidas, celdas y cadena leen biblioteca.sqlite, nunca el original: la etiqueta no debe sugerir lo contrario
        doc = str(a.get("documento", ""))
        doc = f"del documento {doc}" if doc.isdigit() else f"de {Path(doc.replace(chr(92), '/')).name}"
        textos = {
            "buscar": lambda: f"Buscando «{a.get('consulta', '')}»{filtros}",
            "ver": lambda: f"Abriendo el fragmento {a.get('id', '')}",
            "medidas": lambda: f"Consultando medidas en la biblioteca{filtros}",
            "cadena": lambda: f"Siguiendo en la biblioteca las correcciones de molde{filtros}",
            "hallazgo": lambda: f"Abriendo la incidencia {a.get('id', '')}",
            "celdas": lambda: f"Consultando en la biblioteca las celdas {doc}" + (f" · {a['hoja']}" if a.get("hoja") else ""),
            "sql": lambda: "Consultando la biblioteca (SQL)",
            "Read": lambda: f"Leyendo {self._rel(a.get('file_path'))}",
            "Grep": lambda: f"Buscando el texto «{a.get('pattern', '')}» en {self._rel(a.get('path'))}",
            "Glob": lambda: f"Listando {a.get('pattern', '')}",
        }
        return textos[corto]() if corto in textos else corto
