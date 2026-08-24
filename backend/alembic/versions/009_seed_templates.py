"""Seed default document templates.

Revision ID: 009_seed_templates
Revises: 008_templates
Create Date: 2026-07-16
"""

from typing import Union

from alembic import op

revision: str = "009_seed_templates"
down_revision: Union[str, None] = "008_templates"

TECHNICAL_SPECIFICATION = """\
# Technical Specification: [Feature/System Name]

**Author:** [Name]
**Status:** [Draft / In Review / Approved]
**Created:** [Date]
**Last Updated:** [Date]
**Reviewers:** [Names]

---

## 1. Overview

### 1.1 Summary
[One or two sentences describing what this spec covers.]

### 1.2 Background / Problem Statement
[What problem are we solving? Why does it matter now?]

### 1.3 Goals
- [Goal 1]
- [Goal 2]

### 1.4 Non-Goals
- [Explicitly out of scope item 1]
- [Explicitly out of scope item 2]

---

## 2. Requirements

### 2.1 Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | [Description] | Must / Should / Nice-to-have |
| FR-2 | [Description] | Must / Should / Nice-to-have |

### 2.2 Non-Functional Requirements
- **Performance:** [e.g., latency, throughput targets]
- **Scalability:** [expected load, growth]
- **Security:** [auth, data handling, compliance]
- **Reliability:** [uptime, failure tolerance]

---

## 3. Proposed Design

### 3.1 Architecture Overview
[High-level description or diagram reference.]

### 3.2 Components
| Component | Responsibility | Owner |
|-----------|-----------------|-------|
| [Component A] | [What it does] | [Team/Person] |

### 3.3 Data Model
[Schemas, entities, relationships.]

### 3.4 APIs / Interfaces
```
[Endpoint / method signatures / contracts]
```

### 3.5 Sequence / Flow
[Step-by-step flow of a key process.]

---

## 4. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Plan] |

---

## 5. Open Questions

- [ ] [Question 1]
- [ ] [Question 2]

---

## 6. Appendix

[Links to related docs, prior art, references.]\
"""

MEETING_MINUTES = """\
# Meeting Minutes: [Meeting Title]

**Date:** [Date]
**Time:** [Start – End]
**Location / Link:** [Room / Video call link]
**Facilitator:** [Name]
**Note-taker:** [Name]

---

## Attendees
- [Name, Role]
- [Name, Role]

**Absent:** [Name(s)]

---

## Summary
[2-3 sentence high-level recap of what the meeting covered and the key outcomes.]

---

## Agenda
1. [Topic 1]
2. [Topic 2]
3. [Topic 3]

---

## Discussion Notes

### 1. [Topic 1]
- [Key point discussed]
- [Key point discussed]
- **Decision:** [If any]

### 2. [Topic 2]
- [Key point discussed]
- **Decision:** [If any]

### 3. [Topic 3]
- [Key point discussed]
- **Decision:** [If any]

---

## Decisions Made
| # | Decision | Owner | Date |
|---|----------|-------|------|
| 1 | [Decision] | [Name] | [Date] |

---

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|
| 1 | [Action item] | [Name] | [Date] | Not Started |
| 2 | [Action item] | [Name] | [Date] | Not Started |

---

## Parking Lot / Follow-up Topics
- [Item deferred to a future meeting]

---

## Next Meeting
**Date/Time:** [Date]
**Proposed Agenda:** [Topics]\
"""

REVIEWER_FEEDBACK = """\
# Reviewer Feedback: [Item Being Reviewed]

**Reviewer:** [Name]
**Date:** [Date]

---

## 1. Review Scope
[What was reviewed — e.g., PR #402, Spec v1.2, specific files/sections. Include link(s).]

---

## 2. Reviewer Role & Rationale
[Why this person is qualified to review this specific section — relevant expertise, ownership, or context.]

---

## 3. Findings

| # | Severity | Location | Finding |
|---|----------|----------|---------|
| 1 | BLOCKER / MAJOR / MINOR | [File/section/line] | [Description of the issue] |
| 2 | BLOCKER / MAJOR / MINOR | [File/section/line] | [Description of the issue] |

**Severity key:**
- **BLOCKER** — must be resolved before approval/merge
- **MAJOR** — significant concern, should be addressed before approval
- **MINOR** — should be fixed but doesn't block approval

---

## 4. Required Corrections
[Exact, actionable instructions for the Code/Document Agent to implement each fix. One entry per finding, referenced by #.]

1. **[Finding #1]:** [Precise instruction — e.g., "Replace the `for` loop at line 42 with a list comprehension to fix the O(n^2) complexity flagged as BLOCKER."]
2. **[Finding #2]:** [Precise instruction]\
"""

SEED_TEMPLATES = [
    ("Technical Specification", TECHNICAL_SPECIFICATION),
    ("Meeting Minutes", MEETING_MINUTES),
    ("Developer Review", REVIEWER_FEEDBACK),
]


def upgrade() -> None:
    for name, content in SEED_TEMPLATES:
        op.execute(
            "INSERT INTO templates (id, name, content, created_at, updated_at) "
            "VALUES (gen_random_uuid(), "
            f"'{name}', "
            f"$template${content}$template$, "
            "now(), now()) "
            "ON CONFLICT (name) DO NOTHING"
        )


def downgrade() -> None:
    for name, _ in SEED_TEMPLATES:
        op.execute(f"DELETE FROM templates WHERE name = '{name}'")
