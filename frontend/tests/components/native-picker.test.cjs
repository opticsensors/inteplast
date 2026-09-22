const assert = require("node:assert/strict")
const fs = require("node:fs/promises")
const os = require("node:os")
const path = require("node:path")
const { before, test } = require("node:test")
const { build } = require("esbuild")
const { execFile } = require("node:child_process")
let picker, root, outside

before(async () => {
  const result = await build({
    entryPoints: [path.resolve(__dirname, "../../native-picker.ts")],
    bundle: true,
    platform: "node",
    format: "cjs",
    write: false,
  })
  const module = { exports: {} }
  new Function("require", "module", "exports", result.outputFiles[0].text)(
    require,
    module,
    module.exports,
  )
  picker = module.exports
  const scratch = path.join(
    os.homedir(),
    ".codex",
    "scratch",
    "inteplast-native-picker-tests",
    String(process.pid),
  )
  root = path.join(scratch, "Exemples")
  outside = path.join(scratch, "Exemples-other")
  await fs.mkdir(path.join(root, "3212 Pump Housing"), { recursive: true })
  await fs.mkdir(outside, { recursive: true })
})

test("native selections resolve relative paths without accepting sibling roots", async () => {
  assert.equal(
    await picker.selectedRelativePath(
      root,
      path.join(root, "3212 Pump Housing"),
    ),
    "3212 Pump Housing",
  )
  await assert.rejects(
    picker.selectedRelativePath(root, outside),
    /dentro de Exemples/,
  )
  await assert.rejects(
    picker.selectedRelativePath(root, root),
    /dentro de Exemples/,
  )
})

test("closing a picker accepts null and the old empty PowerShell response", () => {
  for (const value of ["", "\r\n", "null\r\n", "\uFEFFnull"])
    assert.equal(picker.parsePickerOutput(value), null)
  assert.equal(
    picker.parsePickerOutput(JSON.stringify("C:\\Exemples\\3212")),
    "C:\\Exemples\\3212",
  )
  assert.throws(() => picker.parsePickerOutput("{}"), /no válida/)
})

test("native dialogs reject cross-origin, remote and unauthenticated requests before opening", async () => {
  let handler
  picker.nativePickerPlugin(root, "http://127.0.0.1:8000").configureServer({
    middlewares: {
      use: (_path, fn) => {
        handler = fn
      },
    },
  })
  for (const [address, origin, expected] of [
    ["127.0.0.1", "http://evil.invalid", 403],
    ["192.168.1.12", "http://localhost:5173", 403],
    [
      "127.0.0.1",
      "http://localhost:5173",
      process.platform === "win32" ? 401 : 503,
    ],
  ]) {
    const response = {
      setHeader() {},
      end(value) {
        this.body = JSON.parse(value)
      },
    }
    await handler(
      {
        method: "POST",
        socket: { remoteAddress: address },
        headers: {
          host: "localhost:5173",
          origin,
          "content-type": "application/json",
        },
      },
      response,
    )
    assert.equal(response.statusCode, expected)
  }
})

test(
  "both Explorer dialogs open at the configured root and closing them returns null",
  {
    skip:
      process.platform !== "win32" ||
      process.env.INTEPLAST_TEST_NATIVE_DIALOG !== "1",
    timeout: 90000,
  },
  async () => {
    // Inspect the real address bar, then close with X and native Cancel. No files selected.
    const initialRoot = path.resolve(
      process.env.INTEPLAST_TEST_PICKER_ROOT ?? root,
    )
    for (const [kind, action] of [
      ["folder", "close"],
      ["file", "close"],
      ["folder", "cancel"],
      ["file", "cancel"],
    ]) {
      await new Promise((resolve, reject) => {
        let status = ""
        let inspection
        const child = execFile(
          "powershell.exe",
          [
            "-NoProfile",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            path.resolve(__dirname, "../../../scripts/native-picker.ps1"),
          ],
          {
            windowsHide: true,
            timeout: 20000,
            env: {
              ...process.env,
              INTEPLAST_PICKER_ROOT: initialRoot,
              INTEPLAST_PICKER_KIND: kind,
            },
          },
          async (error, stdout, stderr) => {
            try {
              if (!inspection)
                throw new Error(
                  `${kind} dialog was never visible: ${error?.message ?? stderr}`,
                )
              await inspection
              assert.ifError(error)
              assert.equal(JSON.parse(stdout.trim()), null)
              resolve()
            } catch (failure) {
              reject(failure)
            }
          },
        )
        child.stdin.end()
        child.stderr.on("data", (chunk) => {
          status += chunk.toString()
          if (!inspection && status.includes("INTEPLAST_PICKER_READY")) {
            inspection = new Promise((done, failed) => {
              execFile(
                "powershell.exe",
                [
                  "-NoProfile",
                  "-STA",
                  "-File",
                  path.join(__dirname, "fixtures/native-picker-driver.ps1"),
                  "-PickerProcessId",
                  String(child.pid),
                  "-ExpectedRoot",
                  initialRoot,
                  "-Action",
                  action,
                ],
                { windowsHide: true, timeout: 15000 },
                (failure) => (failure ? failed(failure) : done()),
              )
            })
            inspection.catch(() => child.kill())
          }
        })
      })
    }
  },
)
