# Kaiwora KB Cloud V5

This release keeps V4.1–V4.4 scoped knowledge, Context Lock semantics, customer-local learning and governed global learning. It hardens the Cloud tenancy registry as an internal service-to-service contract.

`/api/internal/cloud/*` requires `X-Kaiwora-Service-Key`, compared with `KAIWORA_SERVICE_API_KEY`. Node V5 synchronises authenticated SaaS tenants, workspaces and repositories into this registry using stable UUIDs.

The global-learning admin surface remains separately protected by `KAIWORA_ADMIN_API_KEY`. Runtime tenancy credentials and Kaiwora staff admin credentials are intentionally different trust domains.
