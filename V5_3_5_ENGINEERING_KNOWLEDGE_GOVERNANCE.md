# V5.3.5 Engineering Knowledge Governance

## KB Admin changes

`Submit Entry` now supports first-class governance metadata rather than encoding governance inside the content body:

- Knowledge type: Policy, Engineering Rule, Architecture Pattern, Testing Standard, Validation Rule, Task Playbook, Failure Pattern, Repair Playbook, Context Selection Knowledge, Tool Knowledge, Documentation.
- Scope: Global, Tenant, Workspace, Repository.
- Applies-to classification, including `bootstrap_project`.
- Priority.
- Tenant/workspace/repository identifiers when a non-global scope is selected.

The legacy entry `type` remains for backwards compatibility; precise engineering semantics live in `knowledge_kind`.

## Resolver changes

Approved entries remain lifecycle `resolved`. An approved `policy` with `applies_to=bootstrap_project` is deterministically eligible for a repository with no established executable technology stack, even when the ticket wording does not repeat the policy title. Normal engineering knowledge still uses semantic/lexical/outcome-aware resolution.

Resolved knowledge and immutable Context Lock snapshots now retain:

- `knowledge_kind`
- `owner_scope`
- `applies_to`
- `priority`

This lets Agent planning distinguish a mandatory approved policy from advisory documentation.

## Default Tech Stack example

Create an entry with:

- Title: `Default Web Application Technology Stack`
- Knowledge type: `Policy`
- Scope: `Global`
- Applies to: `Bootstrap / greenfield project`
- Priority: `200`
- Status after review: `Resolved` (approved)

The content should define the approved stack but should not prescribe filenames or directory structure.
