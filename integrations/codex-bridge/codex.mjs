import { spawn } from 'node:child_process'
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { dirname, join, relative, resolve, sep } from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'

export const ALLOWED_READS = new Set(['search_catalog', 'search_knowledge', 'read_part', 'read_feature'])
const HERE = dirname(fileURLToPath(import.meta.url))
const MAX_OUTPUT = 256 * 1024

export class BridgeError extends Error {
  constructor(code, message, status = 502) {
    super(message)
    this.code = code
    this.status = status
  }
}

export function validateRequest(value, model) {
  if (!value || typeof value !== 'object' || value.model !== model)
    throw new BridgeError('model_mismatch', 'El modelo del backend no coincide con el del puente.', 400)
  if (!Array.isArray(value.messages) || !value.messages.length || value.messages.length > 40 ||
      !Array.isArray(value.tools) || value.tools.length > ALLOWED_READS.size)
    throw new BridgeError('invalid_request', 'Petición de consulta no válida.', 400)
  for (const message of value.messages) {
    if (!message || !['system', 'user', 'assistant', 'tool'].includes(message.role) ||
        typeof message.content !== 'string' || message.content.length > 100000)
      throw new BridgeError('invalid_request', 'Mensaje de consulta no válido.', 400)
  }
  const names = new Set()
  for (const tool of value.tools) {
    const fn = tool?.function
    if (tool?.type !== 'function' || !ALLOWED_READS.has(fn?.name) || names.has(fn.name) ||
        typeof fn.description !== 'string' || fn.parameters?.type !== 'object')
      throw new BridgeError('invalid_tool', 'Solo se admiten las lecturas de INTEPLAST.', 400)
    names.add(fn.name)
  }
  return value
}

export function outputSchema(tools) {
  const names = tools.map(tool => tool.function.name)
  return {
    type: 'object', additionalProperties: false,
    properties: {
      content: { type: 'string' },
      tool_calls: {
        type: 'array', maxItems: names.length ? 5 : 0,
        items: {
          type: 'object', additionalProperties: false,
          properties: {
            name: names.length ? { type: 'string', enum: names } : { type: 'string' },
            arguments_json: { type: 'string' },
          },
          required: ['name', 'arguments_json'],
        },
      },
    },
    required: ['content', 'tool_calls'],
  }
}

export function decodeAnswer(text, tools) {
  let result
  try { result = JSON.parse(text) } catch {
    throw new BridgeError('invalid_output', 'Codex no ha devuelto una respuesta válida.')
  }
  if (!result || typeof result.content !== 'string' || !Array.isArray(result.tool_calls) ||
      result.tool_calls.length > 5 || result.content.length > 100000)
    throw new BridgeError('invalid_output', 'Formato de respuesta de Codex no válido.')
  const names = new Set(tools.map(tool => tool.function.name))
  const calls = result.tool_calls.map(call => {
    if (!call || !names.has(call.name) || typeof call.arguments_json !== 'string' || call.arguments_json.length > 16000)
      throw new BridgeError('invalid_output', 'Codex ha solicitado una consulta no permitida.')
    let argumentsValue
    try { argumentsValue = JSON.parse(call.arguments_json) } catch {
      throw new BridgeError('invalid_output', 'Los parámetros de consulta de Codex no son válidos.')
    }
    if (!argumentsValue || typeof argumentsValue !== 'object' || Array.isArray(argumentsValue))
      throw new BridgeError('invalid_output', 'Los parámetros de consulta deben ser un objeto.')
    return { function: { name: call.name, arguments: argumentsValue } }
  })
  if (!calls.length && !result.content.trim())
    throw new BridgeError('empty_output', 'Codex no ha generado una respuesta.')
  return { content: calls.length ? '' : result.content, tool_calls: calls, truncated: false }
}

export function commandArgs({ model, effort, directory, schema, instructions }) {
  const args = [
    '--no-daemon', 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
    '--sandbox', 'read-only', '--json', '--color', 'never', '--model', model,
    '--cd', directory, '--output-schema', schema,
    '-c', `model_reasoning_effort=${JSON.stringify(effort)}`,
    '-c', `model_instructions_file=${JSON.stringify(instructions.replaceAll('\\', '/'))}`,
    '-c', 'project_doc_max_bytes=0', '-c', 'web_search="disabled"',
    '-c', 'agents.enabled=false',
  ]
  for (const feature of [
    'shell_tool', 'apps', 'plugins', 'hooks', 'multi_agent', 'multi_agent_v2',
    'browser_use', 'computer_use', 'image_generation', 'view_image', 'memories',
    'skill_search', 'sleep_tool', 'goals', 'tool_suggest',
  ]) args.push('--disable', feature)
  args.push('--enable', 'skip_host_skill_discovery', '-')
  return args
}

function processEnvironment() {
  const keys = new Set([
    'PATH', 'PATHEXT', 'SYSTEMROOT', 'WINDIR', 'USERPROFILE', 'HOME', 'HOMEDRIVE',
    'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'TEMP', 'TMP', 'COMSPEC',
    'CODEX_HOME', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'SSL_CERT_FILE',
  ])
  return Object.fromEntries(Object.entries(process.env).filter(([key]) => keys.has(key.toUpperCase())))
}

export async function runCodex(request, options, signal) {
  const root = resolve(options.runtimeDir)
  await mkdir(root, { recursive: true })
  const directory = await mkdtemp(join(root, 'request-'))
  const work = join(directory, 'work')
  await mkdir(work)
  const schema = join(directory, 'response.json')
  const instructions = join(directory, 'instructions.md')
  await writeFile(schema, JSON.stringify(outputSchema(request.tools)), 'utf8')
  const base = await readFile(join(HERE, 'instructions.md'), 'utf8')
  const system = request.messages.filter(message => message.role === 'system').map(message => message.content).join('\n\n')
  await writeFile(instructions, `${base}\n\nInstrucciones de la aplicación:\n${system}`, 'utf8')
  const prompt = JSON.stringify({
    conversation: request.messages.filter(message => message.role !== 'system'),
    available_reads: request.tools,
  })
  try {
    return await new Promise((resolvePromise, reject) => {
      let child
      let timer
      let complete = false
      let finalText = ''
      let outputSize = 0
      let failure = null
      const finishFailure = error => { failure ??= error; stop() }
      const stop = () => {
        if (!child || child.exitCode !== null || !child.pid) return
        if (process.platform === 'win32') {
          const killer = spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore' })
          killer.on('error', () => child.kill())
        } else child.kill('SIGKILL')
      }
      const onAbort = () => finishFailure(new BridgeError('cancelled', 'Consulta cancelada.', 499))
      child = spawn(options.executable, commandArgs({ ...options, directory: work, schema, instructions }), {
        cwd: work, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'], env: processEnvironment(),
      })
      child.on('error', () => { failure = new BridgeError('codex_unavailable', 'No se puede iniciar Codex en el PC.'); reject(failure) })
      child.stderr.resume() // Never forward CLI diagnostics, credentials or prompts to the web.
      const lines = createInterface({ input: child.stdout })
      lines.on('line', line => {
        outputSize += Buffer.byteLength(line)
        if (outputSize > MAX_OUTPUT) return finishFailure(new BridgeError('output_limit', 'La respuesta de Codex supera el límite.'))
        let event
        try { event = JSON.parse(line) } catch { return }
        if (event.type === 'turn.completed') complete = true
        if (event.type === 'turn.failed' || event.type === 'error')
          finishFailure(new BridgeError('codex_failed', 'Codex no ha podido completar la consulta. Comprueba su sesión y cuota.'))
        if (event.type === 'item.completed' && event.item?.type === 'agent_message') finalText = event.item.text
        if (event.type === 'item.started' && !['agent_message', 'reasoning'].includes(event.item?.type))
          finishFailure(new BridgeError('unexpected_tool', 'Codex intentó una acción fuera de las consultas permitidas.'))
      })
      child.on('close', code => {
        clearTimeout(timer)
        signal?.removeEventListener('abort', onAbort)
        lines.close()
        if (failure) return reject(failure)
        if (code !== 0 || !complete || !finalText)
          return reject(new BridgeError('codex_failed', 'Codex no ha completado la respuesta. Comprueba su sesión y cuota.'))
        try { resolvePromise(decodeAnswer(finalText, request.tools)) } catch (error) { reject(error) }
      })
      child.stdin.on('error', () => {})
      timer = setTimeout(() => finishFailure(new BridgeError('timeout', 'Codex ha tardado demasiado.', 504)), options.timeoutMs)
      signal?.addEventListener('abort', onAbort, { once: true })
      if (signal?.aborted) onAbort()
      else child.stdin.end(prompt)
    })
  } finally {
    // Only remove the single directory just created beneath our private runtime root.
    const childPath = relative(root, resolve(directory))
    if (!childPath.startsWith('request-') || childPath.includes(sep) || childPath.includes('..'))
      throw new Error('Invalid runtime cleanup path')
    await rm(directory, { recursive: true, force: true })
  }
}
