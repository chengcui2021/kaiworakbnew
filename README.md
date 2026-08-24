# Continue KB — Phase 1.5

A workspace-scoped **Knowledge Base** prototype. Earlier Phase 1.5 work hardened the
existing Workspace functionality: workspace **search isolation**, an **active-workspace
label** in the header, a workspace **validation status** panel, and a per-workspace
**activity / audit log**.

**This Evolution adds Approved Knowledge & Context Package foundations**:

- An **approval status** on every KB entry (`draft` → `approved` → `archived`) with
  inline UI controls and activity tracking.
- A dedicated **Approved Knowledge** view, filtered by approval status and scoped to
  the active workspace.
- **Context Packages** — bundles of approved entries carrying a **deterministic
  SHA256 integrity hash**, created through a guarded UI that only allows approved
  entries.

- **Frontend:** Vue 3 + TypeScript + Vite
- **Backend:** Python + FastAPI (in-memory mock data)
- **Runtime:** Docker Compose

## Domain model

| Entity | Notes |
| --- | --- |
| **Workspace** | Isolated knowledge base (id, name, description, document_count). |
| **Document (KB entry)** | Belongs to exactly one workspace via `workspace_id`. Now carries `approval_status` (`draft`/`approved`/`archived`, default `draft`) and `approved_at`. |
| **ContextPackage** | Belongs to a workspace. Fields: `id`, `name`, `workspace_id`, `selected_entry_ids`, `created_at`, `approval_status`, `context_hash`, `entry_titles`. |
| **WorkspaceValidationResult** | Computed on demand; three checks proving isolation. |
| **WorkspaceActivity** | Audit record (`workspace_id`, `event_type`, `timestamp`, `description`, `metadata`). Now also records `document_approved`, `document_archived`, `document_drafted`, `package_created`. |

The store is seeded with three workspaces (`Marketing Q1`, `Engineering Handbook`,
`Personal Notes`). To make the new features immediately observable, two Marketing
entries and one Engineering entry are seeded as **approved**, and one **Context
Package** (`Q1 Launch Context`) is pre-created in Marketing Q1 with a real SHA256 hash.

### Deterministic SHA256 hash

`services/store.py::compute_context_hash` builds the hash from the selected entries
sorted by **id** (order-independent), each reduced to `{id, content}`, serialised with
**canonical JSON** (`sort_keys`, compact separators), and hashed with SHA256. The
result is stored as `sha256:<hex>` and is recomputable by any consumer for integrity
verification.

## Running with Docker Compose

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- The backend host port is **not fixed** — Docker assigns an ephemeral port for the
  container's `8000`. The frontend reaches the backend over the internal compose
  network (`http://backend:8000`) through the Vite dev proxy, so no backend port is
  hard-coded in application code.

## Running locally (without Docker)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (in another terminal)
cd frontend
npm install
npm run dev   # proxies /api -> http://localhost:8000 (override with VITE_PROXY_TARGET)
```

Frontend API calls go through `import.meta.env.VITE_API_BASE_URL` (default empty →
relative `/api` paths proxied by Vite). No `localhost:8009`-style ports are hard-coded.

## Key endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Health check |
| GET/POST | `/api/workspaces` | List / create workspaces |
| GET/PUT/DELETE | `/api/workspaces/{id}` | Read / update / delete workspace |
| GET | `/api/workspaces/{id}/stats` | Workspace statistics |
| GET | `/api/workspaces/{id}/validate` | Run the 3 validation checks |
| GET | `/api/workspaces/{id}/activities?limit=20` | Latest 20 activity records, scoped + newest-first |
| GET/POST | `/api/workspaces/{id}/documents` | List / add documents (scoped). `?approval_status=approved` filters by status. |
| PUT | `/api/workspaces/{id}/documents/{doc_id}/status` | **Change approval status** → records `document_approved` / `document_archived` / `document_drafted` |
| DELETE | `/api/workspaces/{id}/documents/{doc_id}` | Delete a document → records `document_deleted` |
| POST | `/api/workspaces/{id}/documents/{doc_id}/move` | Move a document → records `document_moved` on both workspaces |
| GET/POST | `/api/workspaces/{id}/packages` | **List / create Context Packages** (only approved entries allowed) → records `package_created` |
| GET | `/api/search?workspace_id=…&q=…` | **Workspace-scoped** search |

## Manual verification

1. Header shows **Active Workspace: Marketing Q1 (ws-1)** and now links **Approved
   Knowledge** and **Context Packages**.
2. Open **Marketing Q1** → in **All documents**, each entry shows an **approval badge**
   (Draft/Approved/Archived) and **Draft / Approve / Archive** controls. Click
   **Approve** on *Launch Checklist* → its badge turns Approved and a *"KB entry
   'Launch Checklist' approved"* row appears in the Activity panel.
3. Open **Approved Knowledge** → shows only `approved` entries for the active
   workspace (drafts/archived excluded); switch the header workspace selector and the
   list re-scopes.
4. Open **Context Packages** → the seeded **Q1 Launch Context** package shows its
   workspace, created date, selected entries, **approved** status, and a truncated
   **`sha256:…` hash** with a **Copy** button.
5. In **Create Context Package**, type a name, tick approved entries (only approved
   entries are listed), and **Create Package** → it appears with a freshly computed
   hash and a *"Context Package created"* row in the Activity panel.
6. Search still isolates: search `campaign` in **Marketing Q1** returns the brief; the
   same query in **Engineering Handbook** returns **0 results** (no cross-workspace leak).
7. The **Workspace Validation** panel still shows all three checks green.

## Evolution implementation evidence

This Evolution implements **Approved Knowledge & Context Package foundations**. Each
mandatory requirement maps to concrete generated code:

| # | Requested change | Where it is implemented |
| --- | --- | --- |
| 1 | **Approval status on KB entries** (`draft`/`approved`/`archived`, default `draft`, UI controls, tracked) | `schemas/models.py` (`approval_status`, `approved_at`, `APPROVAL_*`); `store.set_document_status` (records `document_approved`/`document_archived`/`document_drafted`); `PUT …/documents/{id}/status`; UI badge + buttons in `components/DocumentList.vue` + `ApprovalBadge.vue`, wired in `pages/WorkspaceDetailPage.vue`. |
| 2 | **Approved Knowledge view, filtered by workspace** | `pages/ApprovedKnowledgePage.vue` (route `/approved`, header nav link) calls `listDocuments(activeWorkspace, 'approved')`; backend filter in `store.list_documents(..., approval_status=)` + `GET …/documents?approval_status=approved`. Re-scopes on workspace switch; shows approved date metadata. |
| 3 | **Group approved entries into a Context Package** | `pages/ContextPackagesPage.vue` create form (checkbox picker of approved entries only); `POST …/packages` → `store.create_context_package`. |
| 4 | **Package includes name, workspace, selected entries, created date, approval status, context hash** | `ContextPackage` model with all six fields; rendered in the package list of `ContextPackagesPage.vue`. |
| 5 | **Deterministic SHA256 hash from selected approved entries** | `store.compute_context_hash` — entries sorted by id, canonical JSON of `{id, content}`, `sha256:<hex>`. Verified order-independent + reproducible. |
| 6 | **Display the package hash in the UI** | `components/ContextHash.vue` shows the `sha256:…` hash (truncated in list) with **copy-to-clipboard** and an integrity-purpose tooltip. |
| 7 | **Only approved entries can be added to an approved package** | UI lists only approved entries; backend rejects others with `ApprovalConstraintError` → `400` in `routes/packages.py`; package `approval_status` is set to `approved`. |
| 8 | **Keep existing workspace & search functionality working** | Search isolation (`routes/search.py`), validation panel, activity log, workspace/document CRUD all retained and passing; `DocumentList.vue` gained **optional** approval controls (off in search results). |
| 9 | **Do not commit runtime-generated files** | `.gitignore` excludes `node_modules`, `__pycache__`, `.preview_artifacts`, `.prototype_preview.json`, `docs/prototype-*`, and build output. |

### Carried-forward Phase 1 / 1.5 guarantees (still implemented & observable)

- **Workspace search errors fixed / scoped** — `routes/search.py` requires `workspace_id`
  and filters the candidate set *before* text matching, so results can never leak.
- **Active workspace label in header** — `components/WorkspaceIndicator.vue`.
- **Workspace validation status** (search scoped / documents belong / statistics load) —
  `services/workspace_validation.py` + `WorkspaceValidationPanel.vue` on the Workspace page.
- **Docker build & preview** — `backend/Dockerfile`, `frontend/Dockerfile`,
  `docker-compose.yml` (no fixed host backend port); `npm run build` type-checks clean;
  backend imports with `python -c "import app.main"`.

## Project structure

```
backend/
  app/
    main.py                       # FastAPI app + /health + router registration
    routes/                       # workspaces, documents, packages, search
    services/                     # store (in-memory + hash), workspace_validation
    schemas/models.py             # Pydantic models (Document, ContextPackage, ...)
frontend/
  src/
    App.vue                       # shell: header + router-view
    router/                       # routes: workspaces, detail, approved, packages, search
    components/                   # AppHeader, WorkspaceIndicator, validation/activity panels,
                                  #   DocumentList, ApprovalBadge, ContextHash, ...
    pages/                        # Workspaces, WorkspaceDetail, ApprovedKnowledge,
                                  #   ContextPackages, Search
    composables/useWorkspace.ts   # shared active-workspace state
    api/index.ts                  # KB API wrappers (+ preserved legacy exports)
    types/domain.ts               # KB domain types (+ preserved legacy types)
docker-compose.yml
```

## Claude Code (AI-assisted development)

Guardrails live under `.claude/`. Slash commands available in a Claude Code session:

| Command | What it does |
| --- | --- |
| `/test-coverage` | Full coverage audit + writes the missing tests |
| `/weekly-coverage-check` | Lightweight coverage-drift check (detect & report) |
| `/security-audit` (alias `/security-check`) | Read-only dependency report: `npm audit` + `npm outdated` (never modifies `package.json`/lockfile) |
| `/fix-problems` | Sweep & fix the VS Code Problems panel (ESLint + type errors) |

Convention skills auto-surface on each edit via the `inject-skill-pointers` hook — including **`vue-security`** (XSS/`v-html`, `VITE_` secrets, client-trust boundary, IDOR) and **`vue-performance`** (reactivity cost, `markRaw`, list virtualization, lazy imports). `v-html` is pinned to an ESLint warning (`vue/no-v-html`) so every XSS sink is flagged. Full skill list + the Change Protocol: [`frontend/CLAUDE.md`](frontend/CLAUDE.md).
