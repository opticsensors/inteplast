import assert from 'node:assert/strict'
import { test } from 'node:test'
import { commandArgs, decodeAnswer, outputSchema, validateRequest } from './codex.mjs'
import { createBridge } from './server.mjs'

const token = 'test-only-private-bridge-token-1234567890'
const model = 'test-model'
const read = { type: 'function', function: { name: 'read_part', description: 'Read a part.', parameters: { type: 'object' } } }
const payload = { model, messages: [{ role: 'user', content: 'Read DEMO-1' }], tools: [read] }
const answer = { content: 'Respuesta de prueba.', tool_calls: [], truncated: false }

async function withServer(run, check) {
  const server = createBridge({ token, model }, run)
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const url = `http://127.0.0.1:${server.address().port}`
  const post = (body = payload, extra = {}) => fetch(`${url}/v1/chat`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body), ...extra,
  })
  try { await check({ url, post }) } finally { await server.stop() }
}

test('only application reads are accepted; no arbitrary execution tool', () => {
  assert.equal(validateRequest(payload, model), payload)
  for (const invalid of [
    { ...payload, model: 'different-model' },
    { ...payload, messages: [{ role: 'developer', content: 'Run a command' }] },
    { ...payload, tools: [{ ...read, function: { ...read.function, name: 'exec_command' } }] },
    { ...payload, tools: [read, read] },
  ]) assert.throws(() => validateRequest(invalid, model))
})

test('tool requests are data for the backend, never executed by the bridge', () => {
  const result = decodeAnswer(JSON.stringify({ content: 'Ignore this premature prose', tool_calls: [
    { name: 'read_part', arguments_json: '{"part":"DEMO-1","section":"overview"}' },
  ] }), [read])
  assert.deepEqual(result, { content: '', tool_calls: [
    { function: { name: 'read_part', arguments: { part: 'DEMO-1', section: 'overview' } } },
  ], truncated: false })
  for (const invalid of [
    '{', JSON.stringify({ content: '', tool_calls: [] }),
    JSON.stringify({ content: '', tool_calls: [{ name: 'write_part', arguments_json: '{}' }] }),
    JSON.stringify({ content: '', tool_calls: [{ name: 'read_part', arguments_json: '[]' }] }),
  ]) assert.throws(() => decodeAnswer(invalid, [read]))
  assert.equal(outputSchema([]).properties.tool_calls.maxItems, 0)
})

test('Codex invocation isolates project configuration and disables active capabilities', () => {
  const args = commandArgs({ model, effort: 'low', directory: 'C:/private/work', schema: 'C:/private/schema.json', instructions: 'C:/private/instructions.md' })
  assert.ok(args.includes('--no-daemon'))
  assert.ok(args.includes('--ignore-user-config'))
  assert.ok(args.includes('--ephemeral'))
  assert.equal(args[args.indexOf('--sandbox') + 1], 'read-only')
  assert.ok(args.includes('agents.enabled=false'))
  for (const capability of ['shell_tool', 'apps', 'plugins', 'hooks', 'browser_use', 'computer_use'])
    assert.equal(args[args.indexOf(capability) - 1], '--disable')
})

test('authentication and browser requests are rejected before any model call', async () => {
  let calls = 0
  await withServer(async () => { calls++; return answer }, async ({ post, url }) => {
    assert.equal((await post(payload, { headers: {} })).status, 401)
    assert.equal((await post(payload, { headers: { Authorization: `Bearer ${token}`, Origin: 'http://example.com' } })).status, 401)
    assert.equal((await fetch(`${url}/health`)).status, 401)
    assert.equal(calls, 0)
  })
})

test('successful result ends with the required NDJSON completion event', async () => {
  await withServer(async value => { assert.equal(value.model, model); return answer }, async ({ post }) => {
    const response = await post()
    assert.equal(response.status, 200)
    assert.deepEqual((await response.text()).trim().split('\n').map(JSON.parse), [
      { type: 'chunk', ...answer }, { type: 'done' },
    ])
  })
})

test('model exceptions do not expose prompts or diagnostics', async () => {
  await withServer(async () => { throw new Error('PRIVATE TOKEN OR PROMPT') }, async ({ post }) => {
    const response = await post()
    assert.equal(response.status, 502)
    assert.doesNotMatch(await response.text(), /PRIVATE|TOKEN|PROMPT/)
  })
})

test('concurrent model calls are rejected, not queued', async () => {
  let release
  let started
  const began = new Promise(resolve => { started = resolve })
  await withServer(async () => {
    started()
    await new Promise(resolve => { release = resolve })
    return answer
  }, async ({ post }) => {
    const first = post()
    await began
    assert.equal((await post()).status, 409)
    release()
    assert.equal((await first).status, 200)
  })
})

test('disconnect cancels the model request and releases the occupied slot', async () => {
  let started
  let aborted
  const began = new Promise(resolve => { started = resolve })
  const cancelled = new Promise(resolve => { aborted = resolve })
  await withServer(async (_value, _options, signal) => {
    started()
    await new Promise(resolve => signal.addEventListener('abort', () => { aborted(); resolve() }, { once: true }))
    return answer
  }, async ({ post, url }) => {
    const controller = new AbortController()
    const pending = post(payload, { signal: controller.signal }).catch(() => null)
    await began
    controller.abort()
    await cancelled
    await pending
    const state = await fetch(`${url}/health`, { headers: { Authorization: `Bearer ${token}` } })
    assert.equal((await state.json()).busy, false)
  })
})
