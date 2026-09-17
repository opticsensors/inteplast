# INTEPLAST frontend

React + TypeScript, Vite, TanStack Router/Query and Tailwind CSS. Read [the application guide](../docs/app-web.md) before changing feature workflows or the API client.

## Local development

Use Node.js 22.13+ on the 22.x branch, or Node.js 24+, as required by PDF.js. Run these commands from the repository root:

```bash
test -f .env || cp .env.example .env
npm ci
docker compose up -d --build db prestart backend
npm run dev --workspace frontend
```

Open http://localhost:5173. Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` for the local backend, or set the remote API's origin for another deployment. The backend must allow the frontend origin through CORS.

Vite prepares the lazy PDF/3D dependencies at startup and keeps the app cache in
`frontend/node_modules/.vite-app`, separate from standalone Vite checks. Test servers
must use their own cache directory. If a dev tab reports `Outdated Optimize Dep` or
a failed dynamic import after dependency changes, restart with
`npm run dev --workspace frontend -- --force` and reload the tab. This cache is unrelated
to stored documents or generated GLB previews.

Accounts are provisioned by an administrator. The login and `/signup` pages direct account requests to the administrator; they do not offer public registration.

## Feature editing

`/features` is the home catalog for browsing and editing. `/` redirects there, preserving
existing search links. Cards open in read mode and have a direct **Editar** action; the detail
page also offers **Editar**, plus **Eliminar** for the owner or an administrator. Saving or
cancelling returns to that same detail in read mode. Mode changes replace the history entry,
so Back restores the catalog search and scroll position. There is no global editing toggle.

Click the header cover to expand its image or CAD in a modal fitted to the square. CAD starts
automatically, keeping the saved image visible with a small loading indicator while a cancellable worker prepares it. The
corner icon appears on hover/focus and stays visible on touch screens. Cards and the detail
header always use the static image.

In edit mode, clicking the cover (including an empty one) opens one editor with **Imagen**
and **CAD** tabs with identical modal and display dimensions. The editor matches the viewing
modal's width and square; its extra controls add height, with scrolling on shorter screens.
Images support browsing, drag-and-drop and clipboard paste inside
that dialog, outside text fields. The CAD tab uses an already linked part STEP: select faces
in red and frame the view. **Aplicar** applies either result to the header draft;
closing/cancelling the dialog discards only that opening's changes. **Guardar** in the feature
persists the image and annotation together. Changed CAD revisions need a new selection.
The clear-selection icon sits next to the framing control and also restarts an obsolete
selection on the current CAD. See [CAD covers](../docs/portadas-cad.md) for limits and persistence.

- The header is saved with **Guardar**. Background refreshes preserve fields being edited.
- Notes and asset names save automatically after 700 ms. Only locally edited fields are written, and updates for each row run in order.
- Folding a section keeps its editor and pending changes alive. Saving or navigating waits for pending row edits and uploads.
- A failed save retains its draft and displays **Reintentar**. Leaving is blocked until the pending changes are saved or corrected. Reloading or closing the tab with pending changes shows the browser's unsaved-changes warning.
- **Cancelar** discards header changes after pending notes and uploads have finished. Already saved notes and assets remain saved.
- The part selector creates or selects parts; it does not edit existing part codes or names.

## Protected files

The chain icon next to download selects an original from the configured read-only source.
For local references, its dialog offers replacing this asset's file or updating the existing
document's location/revision while retaining its UUID. The latter affects every feature using
that document, as the dialog explains. Missing, changed and
unavailable originals display recovery actions. See [external files](../docs/ficheros-externos.md)
for setup and the real 3212 PDF/STEP verification. Graph is a future adapter.

The file viewer remains a dedicated page. The picker uses a dialog. Part sections retain their
folding state in session storage, and navigation restores scroll by pathname.

File rows display the human-readable asset name and size. Viewer headers omit internal
filenames, paths and revision metadata. Available originals have no status footer; actionable
missing/changed/unavailable messages remain. Metadata is retained for linking and downloads.

`PdfViewer.tsx` uses PDF.js with a locally bundled module worker, loaded only when opening a
PDF. Wheel zoom keeps the point under the cursor fixed; left drag pans the sheet. Plus/minus,
fit and page navigation are available as buttons. Arrow keys pan; +/- zoom and 0 fits. Rendering
uses a temporary canvas so zoom does not blank the sheet, with a 16-megapixel backing limit.
The original PDF remains downloadable; no server-side image copy is created. `nginx.conf`
explicitly serves `.mjs` as JavaScript for the module worker.

`modelControls.ts` uses TrackballControls: left drag rotates in screen space, right/middle drag
pans, and the wheel zooms. Camera up is configured before constructing the controller. Rotation
has no fixed-up pole and stops on release. The triangle counter and gesture footer are omitted.

Images, previews and downloads obtain a short-lived URL from the authenticated `/files/{id}/access-url` endpoint. A plain file UUID is not sufficient to read bytes. Links request authorization metadata without downloading the file contents. Download links ask the server for attachment disposition, including when frontend and API use different origins.

Header images accept JPEG, PNG, GIF, WebP, AVIF and BMP. SVG and other unsupported image types remain downloadable attachments. PDF previews require the `application/pdf` MIME type; the viewer follows what the server can display inline.

3D loading stays lazy. The viewer supports mesh and CAD formats described in [the application guide](../docs/app-web.md); it does not run a desktop CAD application.

Large STL/STEP originals use `WebModelViewer`: it polls the authenticated preview queue and
passes only the cached GLB to `ModelViewer`. Leaving the page stops polling while the server
continues conversion. Download still returns the original. See [web previews](../docs/vistas-3d.md).

## Generated API client

After changing backend endpoints or response models, regenerate `src/client` from the repository root:

```bash
bash scripts/generate-client.sh
```

The script exports `frontend/openapi.json` and regenerates the client. Do not hand-edit generated files. For a manual regeneration, export the backend OpenAPI schema to `frontend/openapi.json` and run `npm run generate-client --workspace frontend`.

## Verification

From the repository root:

```bash
npm exec --workspace frontend -- tsc -p tsconfig.build.json --noEmit
npm run test:components --workspace frontend
```

The component regressions bundle the real React editors and router with an in-memory API. Playwright runs headless with external browser requests blocked. They cover header preservation, folding, refetches, ordered saves, failures, navigation, uploads, external references/relinking and file authorization links. Viewer tests serve a synthetic two-page PDF and the local PDF.js worker, and exercise cursor-anchored zoom, drag/release, page changes, reopening, rotation direction and repeated pole crossings. Install the Playwright browser once if necessary with `npm exec --workspace frontend -- playwright install chromium`.

For end-to-end tests, use the dedicated disposable stack:

```powershell
./scripts/test.ps1 -E2E
```

```bash
bash scripts/test.sh --e2e
```

These scripts use `compose.test.yml`, a separate Compose project and temporary test storage. The Playwright configuration rejects an ordinary application stack. Do not run destructive cleanup against the development stack. The E2E fixtures provision accounts through the test-only API, because public signup is closed.

## Structure

- `src/routes`: authentication, unified feature catalog/detail, file viewers and user administration.
- `src/components/Features`: feature forms, notes, part/file lists and editing save coordination.
- `src/hooks/useFileAccess.ts`: short-lived file authorization URLs.
- `src/client`: generated backend client.
- `tests/components`: isolated regression tests; other `tests/*.spec.ts` files exercise the dedicated E2E stack.
