# Kaiwora Cloud V5.0.1 — KB regression fix

This maintenance release keeps the V5 Cloud tenancy and global-learning model while restoring the governed KB contracts covered by the pre-existing regression suite.

## Fixes

- Correct global-learning sanitisation patterns for URLs, e-mail addresses, repository paths, hashes and identifiers.
- Restore legacy/default Context Lock retrieval without query scope while keeping non-default Cloud locks fail-closed and exact-scope only.
- Carry the frozen governed-context snapshot on newly-created Context Locks; old persisted locks remain readable because the field is optional.
- Remove route-level SQL retrieval machinery from Governed Context Assembly so shared KB services remain the retrieval authority.
- Restore the legacy `workstream` / `shared` resolver selection scopes while retaining tenant owner-scope filtering before ranking.
- Add in-process tenant visibility rechecks as defence in depth after SQL filtering.
- Add explicit Cloud lock regression tests for exact-scope allow, cross-tenant deny and partial-scope deny.

## Expected regression result

The previously observed 10 failures map to these fixes. With the three added Cloud lock tests, the target result is 173 passed, 3 skipped, 0 failed in the same V5 backend test environment.
