# Kaiwora KB: Internal Intelligence Factory and Customer Runtime

Kaiwora uses the same KB service code internally and on customer-controlled nodes.
The difference is deployment role and data, not a forked KB implementation.

## Internal Kaiwora KB

The internal deployment keeps the full Dashboard/UI. It is the engineering-intelligence factory and a normal runtime at the same time.

It is used to:

- curate Knowledge Sources such as Claude Code skills/hooks/conventions, CLAUDE.md, Bastion criteria, architecture/engineering documentation and other reusable sources;
- extract traceable OPEN candidates and govern/approve reusable engineering knowledge;
- run Kaiwora against internal tickets/repos and learn from successful AC evidence;
- maintain shared baseline engineering intelligence that can ship with customer node releases;
- inspect resolver/context-lock behaviour and improve KB quality.

## Customer Kaiwora KB

Each customer Mac mini runs the same KB backend/resolver/learning engine beside Kaiwora Agent and the local model. Customer-specific data is kept in persistent local storage and is not overwritten by software image updates.

The customer flow is automatic:

Ticket + repository -> requirement analysis + repo analysis -> KB resolve (shared baseline + customer-private knowledge) -> Context Lock -> Agent/Qwen patching -> AC evidence -> local governed learning.

The customer does not copy a Context Lock id between products. The lock is an internal service contract between Agent and KB.

## Knowledge scopes

The resolver already separates shared approved knowledge (unassigned workstream) from workstream/customer-specific approved knowledge. Learned evidence additionally supports repository, workspace and tenant scopes. Repository-specific learning cannot leak into unrelated repositories; broader learned knowledge is only reusable after the normal conservative validation/promotion rules.

## Local privacy

Customer-node knowledge resolution defaults to a local OpenAI-compatible embedding endpoint. Source code, ticket text, customer KB contents and run evidence therefore do not need to leave the node. Hosted/Bedrock embeddings remain an explicit configuration option for internal deployments.

## Service boundary

Kaiwora Agent calls the KB service through governed APIs. The important path is `/api/governed-context/lock-from-analysis`; learning evidence is published to `/api/internal/learning/candidates`. `/api/kaiwora/node-profile` identifies whether the deployment is internal or customer without exposing customer content.
