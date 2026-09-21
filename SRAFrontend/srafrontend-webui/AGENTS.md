# AGENTS.md — srafrontend-webui

## Quick commands

```bash
pnpm install          # install deps (uses pnpm 12.4.2)
pnpm dev              # vite dev server (port 5173), proxies /api → localhost:5073
pnpm build            # type-check + vite build (run-p type-check build-only)
pnpm build-only       # vite build only (skip type-check)
pnpm type-check       # vue-tsc --build
pnpm test             # vitest run (single run)
pnpm test:watch       # vitest (watch mode)
pnpm lint             # oxlint --fix then eslint --fix --cache (sequential via run-s)
pnpm lint:oxlint      # oxlint . --fix
pnpm lint:eslint      # eslint . --fix --cache
pnpm format           # prettier --write --experimental-cli src/
```

## Toolchain specifics

- **Package manager**: pnpm 12.4.2 (corepack-managed, pinned in `packageManager` field)
- **Node**: `^22.18.0 || >=24.12.0` (enforced via `engines`)
- **TypeScript**: ~6.0.0, strict with `noUncheckedIndexedAccess: true`
- **Linter**: dual setup — oxlint (fast, Rust-based) runs first, then ESLint. Both configured separately.
- **Formatter**: Prettier 3.9.6 — **no semicolons**, single quotes, 100 char print width
- **Test runner**: Vitest 5.x with jsdom environment (configured per-file via `// @vitest-environment jsdom` comment)
- **UI framework**: Element Plus — components are **auto-imported** via `unplugin-vue-components` (no manual import needed for `El*` components)
- **Auto-imports**: `unplugin-auto-import` is configured for Element Plus resolvers but currently generates an empty `auto-imports.d.ts` — Vue/Pinia APIs are still imported manually

## Architecture

Single-page Vue 3 app (not a monorepo). Entry: `src/main.ts` → `App.vue`.

```
src/
  api/           # API service modules — one file per backend controller
    http.ts      # Axios client with R<T> envelope unwrapping, auth token, error normalization
    configs.ts   # /api/Configs CRUD
    task.ts      # /api/Task run/stop/status
    logs.ts      # SSE log streaming endpoint
    live.ts      # Screenshot polling endpoint
    anno.ts      # External announcements (starrailassistant.top, CORS-enabled)
    openapi.ts   # Fetches OpenAPI spec for dynamic form generation
  components/    # Vue SFCs — many registered globally via unplugin-vue-components
  composables/   # useTaskRunner (polling), useLogStream (SSE with reconnect)
  configs/       # Site metadata (title, author, license)
  router/        # Vue Router — 3 routes: / (eager), /about (lazy), /logs (lazy)
  stores/        # Pinia store (configs only)
  utils/         # Schema form utilities, markdown rendering
  views/         # HomeView, AboutView, LogView
```

## Key patterns to preserve

- **Backend envelope**: All API responses use `R<T>` shape `{ success, message, data }`. The Axios interceptor in `http.ts` auto-unwraps `data` on success and throws `ApiError` on `success=false`. Use `rawEnvelope: true` in request config only when you need to handle `success=false` yourself (e.g. `Task/status` returns `success=false` when idle).
- **Auth token**: Stored in `localStorage` as `sra_token`, attached as `Bearer` header. EventSource (SSE) passes it as `?access_token=` query param since EventSource can't set headers.
- **Dev proxy**: Vite proxies `/api` and `/openapi` to `http://localhost:5073` (the .NET backend). Logs SSE endpoint is `/api/backend/logs/stream`, screenshot is `/api/backend/screenshot`.
- **OpenAPI-driven forms**: `TasksConfigPanel` component fetches `/openapi/v1.json` and generates form fields dynamically from the OpenAPI schema — config structure is defined by the backend, not the frontend.
- **Test mocking**: API tests mock `request` from `http.ts` (not Axios directly). HTTP-level tests swap `http.defaults.adapter` to avoid network calls. Tests live alongside source in `__tests__/` directories.
- **Locale**: `index.html` sets `<html lang="zh">`. UI text is in Chinese. Comments in code are also in Chinese.

## Verification order

After making changes, run in this order:

```bash
pnpm lint        # oxlint + eslint
pnpm type-check  # vue-tsc --build
pnpm test        # vitest run
pnpm build       # full production build
```
