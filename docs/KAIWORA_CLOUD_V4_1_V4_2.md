# Kaiwora Cloud V4.1 + V4.2

## Cloud tenancy

Alembic revision `017_cloud_multi_tenant_scopes` adds:

- `tenants`
- `cloud_workspaces`
- `cloud_repositories`
- ownership columns on `entries`
- ownership columns on `context_assembly_locks`

The tenancy registry is an internal control-plane foundation. Authentication, signup and billing are intentionally outside this release.

## Governed knowledge scopes

Knowledge entries support:

- `global`: Kaiwora Master KB, visible to all tenants
- `tenant`: visible only to one tenant
- `workspace`: visible only to one tenant/workspace
- `repository`: visible only to one tenant/workspace/repository

Both semantic retrieval and lexical fallback apply the scope predicate in the database query before ranking. Explicit entry selection is separately checked to prevent bypassing the resolver with another tenant's entry ID.

## Context Lock ownership

Analysis-aware Context Locks persist `tenant_id`, `workspace_id`, and `repository_id`. Lock retrieval/status endpoints require the same identity and return 404 on ownership mismatch. Tenant/workspace/repository identity is frozen into requirement context and therefore affects the context hash.

## Existing governed execution semantics retained

Repository file `context_role` and `access` semantics remain intact, including `verification/read_only` files such as protected validation context.
