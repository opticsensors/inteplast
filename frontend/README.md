# INTEPLAST frontend

React + TypeScript, Vite, TanStack Router/Query and Tailwind CSS. Read [the application guide](../docs/app-web.md) before changing feature workflows or the API client.

## Local development

Use Node.js 22 or later. Run these commands from the repository root:

```bash
npm ci
docker compose up -d --build db prestart backend
npm run dev --workspace frontend
```

Open http://localhost:5173. Set `VITE_API_URL=http://localhost:8000` in `frontend/.env` for the local backend, or set the remote API's origin for another deployment. The backend must allow the frontend origin through CORS.

Accounts are provisioned by an administrator. The login and `/signup` pages direct account requests to the administrator; they do not offer public registration.

## Feature editing

- The header is saved with **Guardar**. Background refreshes preserve fields being edited.
- Notes and asset names save automatically after 700 ms. Only locally edited fields are written, and updates for each row run in order.
- Folding a section keeps its editor and pending changes alive. Saving or navigating waits for pending row edits and uploads.
- A failed save retains its draft and displays **Reintentar**. Leaving is blocked until the pending changes are saved or corrected. Reloading or closing the tab with pending changes shows the browser's unsaved-changes warning.
- **Cancelar** discards header changes after pending notes and uploads have finished. Already saved notes and assets remain saved.
- The part selector creates or selects parts; it does not edit existing part codes or names.

## Protected files

Images, previews and downloads obtain a short-lived URL from the authenticated `/files/{id}/access-url` endpoint. A plain file UUID is not sufficient to read bytes. Links request authorization metadata without downloading the file contents. Download links ask the server for attachment disposition, including when frontend and API use different origins.

Header images accept JPEG, PNG, GIF, WebP, AVIF and BMP. SVG and other unsupported image types remain downloadable attachments. PDF previews require the `application/pdf` MIME type; the viewer follows what the server can display inline.

3D loading stays lazy. The viewer supports mesh and CAD formats described in [the application guide](../docs/app-web.md); it does not run a desktop CAD application.

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

The component regressions bundle the real React editors and router with an in-memory API. Playwright runs headless with all outbound browser requests blocked. They cover header preservation, folding, refetches, ordered saves, failures, navigation, uploads and file authorization links. Install the Playwright browser once if necessary with `npm exec --workspace frontend -- playwright install chromium`.

For end-to-end tests, use the dedicated disposable stack:

```powershell
./scripts/test.ps1 -E2E
```

```bash
bash scripts/test.sh --e2e
```

These scripts use `compose.test.yml`, a separate Compose project and temporary test storage. The Playwright configuration rejects an ordinary application stack. Do not run destructive cleanup against the development stack. The E2E fixtures provision accounts through the test-only API, because public signup is closed.

## Structure

- `src/routes`: authentication, dashboard, feature management/detail, file viewers and user administration.
- `src/components/Features`: feature forms, notes, part/file lists and editing save coordination.
- `src/hooks/useFileAccess.ts`: short-lived file authorization URLs.
- `src/client`: generated backend client.
- `tests/components`: isolated regression tests; other `tests/*.spec.ts` files exercise the dedicated E2E stack.
