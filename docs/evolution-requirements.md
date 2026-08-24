# Evolution Requirements for Prototype Generation

If this file contains requested changes or acceptance criteria, they are mandatory for the next prototype version.
Do not treat them as comments, history, or optional notes. Implement them in the generated UI/workflow/data model where applicable.

## Evolution Request

**Context:** This evolution builds upon the workspace isolation fixes, validation system, and activity tracking from earlier Phase 1.5 work. The foundation of reliable workspace scoping and audit trails is now in place, enabling us to add formal knowledge approval workflows and cryptographically-verifiable context packaging with confidence that all operations will be correctly scoped and tracked.

**Mandatory Changes:**

1. **Add Approval Status to KB Entries**
   - Extend KB entry data model with `approval_status` field
   - Support three states: `draft`, `approved`, `archived`
   - Default new entries to `draft` status
   - Add UI controls to change approval status
   - Track approval status changes in activity log

2. **Implement Approved Knowledge View**
   - Create new view/page for "Approved Knowledge"
   - Filter KB entries by `approval_status = 'approved'`
   - Maintain workspace isolation (only show approved entries from selected workspace)
   - Display approval metadata (approved date, if available)
   - Provide clear visual distinction from all-entries view

3. **Create Context Package Data Model**
   - New entity: `ContextPackage`
   - Fields:
     - `id`: UUID
     - `name`: string (required)
     - `workspace_id`: UUID (foreign key, required)
     - `selected_entry_ids`: array of UUIDs (KB entry IDs)
     - `created_at`: timestamp
     - `approval_status`: enum (draft/approved/archived)
     - `context_hash`: string (SHA256 hash)
   - Relationship: ContextPackage belongs to Workspace
   - Relationship: ContextPackage references multiple KB entries

4. **Implement Context Package Creation**
   - Add "Create Context Package" UI in workspace view
   - Package creation form with:
     - Name input (required)
     - Workspace (auto-populated, read-only)
     - KB entry selection (checkboxes, only approved entries shown)
     - Create button
   - Validation: only approved KB entries can be selected
   - Validation: package name is required
   - On creation:
     - Store selected entry IDs
     - Set created timestamp
     - Compute and store SHA256 hash
     - Set approval_status based on selected entries (approved if all entries approved)
     - Record activity in workspace log

5. **Implement Deterministic SHA256 Hash Generation**
   - Hash input: concatenation of selected KB entry IDs + entry content
   - Sort entry IDs deterministically (e.g., alphabetically) before hashing
   - Use canonical JSON serialization for consistent hashing
   - Hash format: `sha256:<hex_digest>`
   - Store hash in `context_hash` field
   - Hash must be recomputable from package data for verification

6. **Display Context Package Hash in UI**
   - Show hash prominently in package detail view
   - Format: `sha256:a3f2b8c4d5e6f7...` (full hash or truncated with tooltip)
   - Provide copy-to-clipboard functionality
   - Indicate hash purpose (integrity verification)
   - Show hash in package list view (truncated)

7. **Enforce Approval Constraints**
   - Context Package creation UI: only show approved KB entries for selection
   - API validation: reject package creation if any selected entry is not approved
   - Package approval_status: automatically set to "approved" if all entries are approved
   - Prevent adding draft or archived entries to approved packages

8. **Activity Tracking for New Features**
   - Track "KB entry approved" events
   - Track "KB entry archived" events
   - Track "Context Package created" events
   - Track "Context Package updated" events (if editing is supported)
   - All events include workspace_id for scoping
   - All events include timestamps

9. **Integration with Existing Features**
   - Approval workflow must not break existing workspace search

## Evolution Request
- Continue KB Phase 1.5 by adding Approved Knowledge and Context Package foundations.
- Requirements:
- 1. Add an approval status for KB entries:
- draft
- approved
- archived
- 2. Add an Approved Knowledge view filtered by workspace.
- 3. Allow approved entries to be grouped into a Context Package.
- 4. Each Context Package should include:
- package name
- workspace
- selected KB entries
- created date
- approval status
- context hash
- 5. Generate a deterministic SHA256 hash for each Context Package based on its selected approved entries.
- 6. Display the Context Package hash in the UI.
- 7. Ensure only approved KB entries can be added to an approved Context Package.
- 8. Keep existing workspace and search functionality working.
- 9. Do not commit runtime-generated files or artifacts.
## Mandatory Acceptance Criteria
- The next prototype must visibly implement: Continue KB Phase 1.5 by adding Approved Knowledge and Context Package foundations.
- The next prototype must visibly implement: Requirements:
- The next prototype must visibly implement: 1. Add an approval status for KB entries:
- The next prototype must visibly implement: draft
- The next prototype must visibly implement: approved
- The next prototype must visibly implement: archived
- The next prototype must visibly implement: 2. Add an Approved Knowledge view filtered by workspace.
- The next prototype must visibly implement: 3. Allow approved entries to be grouped into a Context Package.
- The next prototype must visibly implement: 4. Each Context Package should include:
- The next prototype must visibly implement: package name
- The next prototype must visibly implement: workspace
- The next prototype must visibly implement: selected KB entries
- The next prototype must visibly implement: created date
- The next prototype must visibly implement: approval status
- The next prototype must visibly implement: context hash
- The next prototype must visibly implement: 5. Generate a deterministic SHA256 hash for each Context Package based on its selected approved entries.
- The next prototype must visibly implement: 6. Display the Context Package hash in the UI.
- The next prototype must visibly implement: 7. Ensure only approved KB entries can be added to an approved Context Package.
- The next prototype must visibly implement: 8. Keep existing workspace and search functionality working.
- The next prototype must visibly implement: 9. Do not commit runtime-generated files or artifacts.
## Prototype Implementation Guidance
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: Continue KB Phase 1.5 by adding Approved Knowledge and Context Package foundations.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: Requirements:
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 1. Add an approval status for KB entries:
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: draft
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: approved
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: archived
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 2. Add an Approved Knowledge view filtered by workspace.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 3. Allow approved entries to be grouped into a Context Package.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 4. Each Context Package should include:
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: package name
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: workspace
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: selected KB entries
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: created date
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: approval status
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: context hash
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 5. Generate a deterministic SHA256 hash for each Context Package based on its selected approved entries.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 6. Display the Context Package hash in the UI.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 7. Ensure only approved KB entries can be added to an approved Context Package.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 8. Keep existing workspace and search functionality working.
- Update the generated UI, workflow, data model, or interactions as needed to satisfy: 9. Do not commit runtime-generated files or artifacts.
## Evolution Validation Notes
- Browser preview evidence must prove the following feedback is implemented: Continue KB Phase 1.5 by adding Approved Knowledge and Context Package foundations.
- Browser preview evidence must prove the following feedback is implemented: Requirements:
- Browser preview evidence must prove the following feedback is implemented: 1. Add an approval status for KB entries:
- Browser preview evidence must prove the following feedback is implemented: draft
- Browser preview evidence must prove the following feedback is implemented: approved
- Browser preview evidence must prove the following feedback is implemented: archived
- Browser preview evidence must prove the following feedback is implemented: 2. Add an Approved Knowledge view filtered by workspace.
- Browser preview evidence must prove the following feedback is implemented: 3. Allow approved entries to be grouped into a Context Package.
- Browser preview evidence must prove the following feedback is implemented: 4. Each Context Package should include:
- Browser preview evidence must prove the following feedback is implemented: package name
- Browser preview evidence must prove the following feedback is implemented: workspace
- Browser preview evidence must prove the following feedback is implemented: selected KB entries
- Browser preview evidence must prove the following feedback is implemented: created date
- Browser preview evidence must prove the following feedback is implemented: approval status
- Browser preview evidence must prove the following feedback is implemented: context hash
- Browser preview evidence must prove the following feedback is implemented: 5. Generate a deterministic SHA256 hash for each Context Package based on its selected approved entries.
- Browser preview evidence must prove the following feedback is implemented: 6. Display the Context Package hash in the UI.
- Browser preview evidence must prove the following feedback is implemented: 7. Ensure only approved KB entries can be added to an approved Context Package.
- Browser preview evidence must prove the following feedback is implemented: 8. Keep existing workspace and search functionality working.
- Browser preview evidence must prove the following feedback is implemented: 9. Do not commit runtime-generated files or artifacts.
