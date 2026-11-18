import { createServer } from 'node:http'
import { timingSafeEqual } from 'node:crypto'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { BridgeError, runCodex, validateRequest } from './codex.mjs'

const MAX_BODY = 256 * 1024

function authorized(header, token) {
  const actual = Buffer.from(header ?? '')
  const expected = Buffer.from(`Bearer ${token}`)
  return actual.length === expected.length && timingSafeEqual(actual, expected)
}

async function bodyJson(request) {
  let size = 0
  const chunks = []
  for await (const chunk of request) {
    size += chunk.length
    if (size > MAX_BODY) throw new BridgeError('body_limit', 'Petición demasiado grande.', 413)
    chunks.push(chunk)
  }
  try { return JSON.parse(Buffer.concat(chunks).toString('utf8')) } catch {
    throw new BridgeError('invalid_json', 'Petición JSON no válida.', 400)
  }
}

export function createBridge(options, runner = runCodex) {
  if (!options.token || options.token.length < 32) throw new Error('The bridge needs a private token of at least 32 characters')
  let busy = false
  const controllers = new Set()
  const server = createServer(async (request, response) => {
    const send = (status, value) => {
      if (response.destroyed) return
      response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
      response.end(JSON.stringify(value))
    }
    if (request.headers.origin || !authorized(request.headers.authorization, options.token))
      return send(401, { error: 'No autorizado.' })
    if (request.method === 'GET' && request.url === '/health')
      return send(200, { ready: true, model: options.model, busy })
    if (request.method !== 'POST' || request.url !== '/v1/chat') return send(404, { error: 'Ruta no disponible.' })
    if (busy) return send(409, { error: 'Codex está atendiendo otra consulta.' })
    busy = true
    const controller = new AbortController()
    controllers.add(controller)
    response.on('close', () => { if (!response.writableEnded) controller.abort() })
    try {
      const payload = validateRequest(await bodyJson(request), options.model)
      const result = await runner(payload, options, controller.signal)
      if (!response.destroyed) {
        response.writeHead(200, { 'Content-Type': 'application/x-ndjson', 'Cache-Control': 'no-store' })
        response.end(`${JSON.stringify({ type: 'chunk', ...result })}\n${JSON.stringify({ type: 'done' })}\n`)
      }
    } catch (error) {
      const known = error instanceof BridgeError
      send(known ? error.status : 502, { error: known ? error.message : 'El puente de Codex no ha podido completar la consulta.' })
    } finally {
      controllers.delete(controller)
      busy = false
    }
  })
  server.headersTimeout = 10000
  server.requestTimeout = 15000
  server.stop = async () => {
    for (const controller of controllers) controller.abort()
    server.closeAllConnections()
    await new Promise(resolveStop => server.close(resolveStop))
  }
  return server
}

async function main() {
  const tokenFile = process.env.CODEX_BRIDGE_TOKEN_FILE
  if (!tokenFile) throw new Error('Set CODEX_BRIDGE_TOKEN_FILE to a private file outside the repository')
  const options = {
    token: (await readFile(tokenFile, 'utf8')).trim(),
    model: process.env.CODEX_BRIDGE_MODEL || 'gpt-reserve',
    effort: process.env.CODEX_BRIDGE_EFFORT || 'low',
    executable: process.env.CODEX_BRIDGE_EXECUTABLE || 'codex',
    runtimeDir: process.env.CODEX_BRIDGE_RUNTIME_DIR || resolve(dirname(tokenFile), 'runtime'),
    timeoutMs: Number(process.env.CODEX_BRIDGE_TIMEOUT_SECONDS || 110) * 1000,
  }
  if (!['low', 'medium', 'high'].includes(options.effort) || !Number.isFinite(options.timeoutMs) || options.timeoutMs < 1000)
    throw new Error('Invalid bridge configuration')
  const host = process.env.CODEX_BRIDGE_HOST || '127.0.0.1'
  const port = Number(process.env.CODEX_BRIDGE_PORT || 11435)
  const server = createBridge(options)
  server.listen(port, host, () => process.stdout.write(`INTEPLAST Codex bridge listening on ${host}:${port} (${options.model}, ${options.effort})\n`))
  for (const event of ['SIGINT', 'SIGTERM']) process.once(event, () => { void server.stop() })
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  main().catch(() => { process.stderr.write('Cannot start Codex bridge: check the private configuration.\n'); process.exitCode = 1 })
