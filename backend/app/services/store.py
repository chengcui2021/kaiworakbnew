"""In-memory data store for the Knowledge Base prototype.

Holds workspaces and documents. All document access is intended to be
scoped by ``workspace_id`` so that workspace isolation is preserved.
This is mock/in-memory data only -- no database is used.
"""
from __future__ import annotations

import hashlib
import itertools
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.schemas.models import (
    APPROVAL_APPROVED,
    APPROVAL_ARCHIVED,
    APPROVAL_DRAFT,
    APPROVAL_STATUSES,
    EVENT_DOCUMENT_APPROVED,
    EVENT_DOCUMENT_ARCHIVED,
    EVENT_DOCUMENT_DELETED,
    EVENT_DOCUMENT_DRAFTED,
    EVENT_DOCUMENT_MOVED,
    EVENT_DOCUMENT_UPLOADED,
    EVENT_PACKAGE_CREATED,
    EVENT_WORKSPACE_CREATED,
    EVENT_WORKSPACE_RENAMED,
    ContextPackage,
    Document,
    Workspace,
    WorkspaceActivity,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApprovalConstraintError(Exception):
    """Raised when a Context Package would include non-approved entries."""

    def __init__(self, entry_ids: list[str]) -> None:
        self.entry_ids = entry_ids
        super().__init__(f"Entries not approved: {entry_ids}")


def compute_context_hash(entries: list[Document]) -> str:
    """Deterministic SHA256 over the selected entries.

    The payload is the entries sorted by id (so ordering is irrelevant), each
    reduced to ``{id, content}`` and serialised with canonical JSON. This makes
    the hash recomputable by any consumer for integrity verification.
    """
    payload = [
        {"id": e.id, "content": e.content}
        for e in sorted(entries, key=lambda d: d.id)
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class WorkspaceStore:
    def __init__(self) -> None:
        self._workspaces: dict[str, Workspace] = {}
        self._documents: dict[str, Document] = {}
        # Activity / audit log. Stored newest-last; queries return newest-first.
        self._activities: list[WorkspaceActivity] = []
        # Context packages keyed by id.
        self._packages: dict[str, ContextPackage] = {}
        self._ws_counter = itertools.count(1)
        self._doc_counter = itertools.count(1)
        self._act_counter = itertools.count(1)
        self._pkg_counter = itertools.count(1)
        self._seed()

    # ------------------------------------------------------------------
    # seeding
    # ------------------------------------------------------------------
    def _seed(self) -> None:
        ws_a = self._make_workspace(
            "Marketing Q1",
            "Campaign briefs, launch plans and brand guidelines for the Q1 push.",
        )
        ws_b = self._make_workspace(
            "Engineering Handbook",
            "Architecture decisions, runbooks and onboarding docs for the platform team.",
        )
        ws_c = self._make_workspace(
            "Personal Notes",
            "Private research notes kept isolated from work knowledge bases.",
        )

        brief = self._make_document(ws_a.id, "Q1 Campaign Brief",
                            "The launch campaign focuses on workspace isolation and reliability messaging.")
        voice = self._make_document(ws_a.id, "Brand Voice Guidelines",
                            "Keep messaging confident and clear. Emphasise trust and reliability.")
        self._make_document(ws_a.id, "Launch Checklist",
                            "Confirm landing page, email sequence and analytics tracking before launch.")

        runbook = self._make_document(ws_b.id, "Search Service Runbook",
                            "Every search query MUST include a workspace_id filter to preserve isolation.")
        self._make_document(ws_b.id, "Onboarding Guide",
                            "New engineers should read the architecture overview and the reliability checklist.")

        self._make_document(ws_c.id, "Reading List",
                            "Books and articles on knowledge management and reliable search systems.")

        # Seed approval statuses so the Approved Knowledge view and Context
        # Package creation are immediately observable in the preview.
        # Approve two Marketing entries and one Engineering entry; leave the
        # rest as drafts (the default). Statuses are backdated for realism.
        base = datetime.now(timezone.utc)
        approved_ts = (base - timedelta(hours=2)).isoformat()
        for doc in (brief, voice, runbook):
            doc.approval_status = APPROVAL_APPROVED
            doc.approved_at = approved_ts

        # Seed a realistic, backdated activity history so the Activity panel is
        # immediately observable in the preview. Existing data without history
        # remains valid -- activity records are additive and never required.
        self._seed_activities(ws_a, ws_b, ws_c)

        # Record approval events for the seeded approvals.
        self._record(ws_a.id, EVENT_DOCUMENT_APPROVED,
                     f"KB entry '{brief.title}' approved", ts=approved_ts,
                     metadata={"document_id": brief.id, "document_title": brief.title})
        self._record(ws_a.id, EVENT_DOCUMENT_APPROVED,
                     f"KB entry '{voice.title}' approved", ts=approved_ts,
                     metadata={"document_id": voice.id, "document_title": voice.title})
        self._record(ws_b.id, EVENT_DOCUMENT_APPROVED,
                     f"KB entry '{runbook.title}' approved", ts=approved_ts,
                     metadata={"document_id": runbook.id, "document_title": runbook.title})

        # Seed one Context Package in Marketing Q1 from its two approved entries
        # so the package list and its hash are visible on first load.
        self.create_context_package(
            ws_a.id, "Q1 Launch Context", [brief.id, voice.id],
        )

    def _seed_activities(self, ws_a: Workspace, ws_b: Workspace, ws_c: Workspace) -> None:
        base = datetime.now(timezone.utc)

        def ago(**kwargs) -> str:
            return (base - timedelta(**kwargs)).isoformat()

        # Workspace creation events (oldest).
        self._record(ws_a.id, EVENT_WORKSPACE_CREATED,
                     f"Workspace '{ws_a.name}' created", ts=ago(days=6),
                     metadata={"workspace_name": ws_a.name})
        self._record(ws_b.id, EVENT_WORKSPACE_CREATED,
                     f"Workspace '{ws_b.name}' created", ts=ago(days=5, hours=3),
                     metadata={"workspace_name": ws_b.name})
        self._record(ws_c.id, EVENT_WORKSPACE_CREATED,
                     f"Workspace '{ws_c.name}' created", ts=ago(days=4),
                     metadata={"workspace_name": ws_c.name})

        # Document uploads.
        self._record(ws_a.id, EVENT_DOCUMENT_UPLOADED,
                     "Document 'Q1 Campaign Brief' uploaded", ts=ago(days=3, hours=5),
                     metadata={"document_title": "Q1 Campaign Brief"})
        self._record(ws_a.id, EVENT_DOCUMENT_UPLOADED,
                     "Document 'Brand Voice Guidelines' uploaded", ts=ago(days=2, hours=2),
                     metadata={"document_title": "Brand Voice Guidelines"})
        self._record(ws_b.id, EVENT_DOCUMENT_UPLOADED,
                     "Document 'Search Service Runbook' uploaded", ts=ago(days=2),
                     metadata={"document_title": "Search Service Runbook"})

        # A rename event.
        self._record(ws_a.id, EVENT_WORKSPACE_RENAMED,
                     "Workspace renamed from 'Marketing' to 'Marketing Q1'", ts=ago(days=1, hours=4),
                     metadata={"old_name": "Marketing", "new_name": ws_a.name})

        # A delete event (record persists even though the doc is gone).
        self._record(ws_b.id, EVENT_DOCUMENT_DELETED,
                     "Document 'Legacy Notes' deleted", ts=ago(hours=6),
                     metadata={"document_title": "Legacy Notes"})

        # A cross-workspace move (recorded on both source and destination).
        self._record(ws_c.id, EVENT_DOCUMENT_MOVED,
                     f"Document 'Reliability Checklist' moved to '{ws_b.name}'", ts=ago(hours=3),
                     metadata={"document_title": "Reliability Checklist",
                               "from_workspace": ws_c.name, "to_workspace": ws_b.name})
        self._record(ws_b.id, EVENT_DOCUMENT_MOVED,
                     f"Document 'Reliability Checklist' moved from '{ws_c.name}'", ts=ago(hours=3),
                     metadata={"document_title": "Reliability Checklist",
                               "from_workspace": ws_c.name, "to_workspace": ws_b.name})

    # ------------------------------------------------------------------
    # workspaces
    # ------------------------------------------------------------------
    def _make_workspace(self, name: str, description: str = "") -> Workspace:
        ts = _now()
        ws = Workspace(
            id=f"ws-{next(self._ws_counter)}",
            name=name,
            description=description,
            created_at=ts,
            updated_at=ts,
            document_count=0,
        )
        self._workspaces[ws.id] = ws
        return ws

    def list_workspaces(self) -> list[Workspace]:
        result = []
        for ws in self._workspaces.values():
            ws.document_count = self._count_documents(ws.id)
            result.append(ws)
        return result

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        ws = self._workspaces.get(workspace_id)
        if ws:
            ws.document_count = self._count_documents(ws.id)
        return ws

    def create_workspace(self, name: str, description: str = "") -> Workspace:
        ws = self._make_workspace(name, description)
        self._record(ws.id, EVENT_WORKSPACE_CREATED,
                     f"Workspace '{ws.name}' created",
                     metadata={"workspace_name": ws.name})
        return ws

    def update_workspace(self, workspace_id: str, name: Optional[str],
                         description: Optional[str]) -> Optional[Workspace]:
        ws = self._workspaces.get(workspace_id)
        if not ws:
            return None
        old_name = ws.name
        if name is not None:
            ws.name = name
        if description is not None:
            ws.description = description
        ws.updated_at = _now()
        ws.document_count = self._count_documents(ws.id)
        # Record a rename only when the name actually changed.
        if name is not None and name != old_name:
            self._record(ws.id, EVENT_WORKSPACE_RENAMED,
                         f"Workspace renamed from '{old_name}' to '{ws.name}'",
                         metadata={"old_name": old_name, "new_name": ws.name})
        return ws

    def delete_workspace(self, workspace_id: str) -> bool:
        if workspace_id not in self._workspaces:
            return False
        # Cascade delete documents to avoid orphaned records.
        for doc_id in [d.id for d in self._documents.values() if d.workspace_id == workspace_id]:
            del self._documents[doc_id]
        del self._workspaces[workspace_id]
        return True

    # ------------------------------------------------------------------
    # documents (always scoped by workspace)
    # ------------------------------------------------------------------
    def _make_document(self, workspace_id: str, title: str, content: str) -> Document:
        ts = _now()
        doc = Document(
            id=f"doc-{next(self._doc_counter)}",
            workspace_id=workspace_id,
            title=title,
            content=content,
            created_at=ts,
            updated_at=ts,
        )
        self._documents[doc.id] = doc
        return doc

    def _count_documents(self, workspace_id: str) -> int:
        return sum(1 for d in self._documents.values() if d.workspace_id == workspace_id)

    def list_documents(
        self, workspace_id: str, approval_status: Optional[str] = None,
    ) -> list[Document]:
        """Return documents belonging ONLY to the given workspace.

        When ``approval_status`` is provided, results are additionally filtered
        by status (e.g. only ``approved`` entries) while remaining workspace
        scoped -- this powers the Approved Knowledge view without ever leaking
        across workspaces.
        """
        docs = [d for d in self._documents.values() if d.workspace_id == workspace_id]
        if approval_status:
            docs = [d for d in docs if d.approval_status == approval_status]
        return docs

    def all_documents(self) -> list[Document]:
        """Unscoped access -- used only by validation to prove isolation."""
        return list(self._documents.values())

    def create_document(self, workspace_id: str, title: str, content: str) -> Document:
        doc = self._make_document(workspace_id, title, content)
        self._record(workspace_id, EVENT_DOCUMENT_UPLOADED,
                     f"Document '{doc.title}' uploaded",
                     metadata={"document_id": doc.id, "document_title": doc.title})
        return doc

    def get_document(self, workspace_id: str, document_id: str) -> Optional[Document]:
        doc = self._documents.get(document_id)
        if doc is None or doc.workspace_id != workspace_id:
            return None
        return doc

    def delete_document(self, workspace_id: str, document_id: str) -> bool:
        """Delete a document scoped to its workspace and record the event."""
        doc = self.get_document(workspace_id, document_id)
        if doc is None:
            return False
        del self._documents[document_id]
        # The activity record persists even though the document is gone.
        self._record(workspace_id, EVENT_DOCUMENT_DELETED,
                     f"Document '{doc.title}' deleted",
                     metadata={"document_id": doc.id, "document_title": doc.title})
        return True

    def move_document(self, workspace_id: str, document_id: str,
                      target_workspace_id: str) -> Optional[Document]:
        """Move a document to another workspace, recording the event on both."""
        doc = self.get_document(workspace_id, document_id)
        if doc is None:
            return None
        source = self._workspaces.get(workspace_id)
        target = self._workspaces.get(target_workspace_id)
        if target is None or source is None:
            raise KeyError(target_workspace_id)
        doc.workspace_id = target_workspace_id
        doc.updated_at = _now()
        # Record on the source (left) and destination (arrived) workspaces so the
        # move is visible in both activity feeds, scoped correctly.
        self._record(source.id, EVENT_DOCUMENT_MOVED,
                     f"Document '{doc.title}' moved to '{target.name}'",
                     metadata={"document_id": doc.id, "document_title": doc.title,
                               "from_workspace": source.name, "to_workspace": target.name})
        self._record(target.id, EVENT_DOCUMENT_MOVED,
                     f"Document '{doc.title}' moved from '{source.name}'",
                     metadata={"document_id": doc.id, "document_title": doc.title,
                               "from_workspace": source.name, "to_workspace": target.name})
        return doc

    # ------------------------------------------------------------------
    # approval status (draft -> approved -> archived)
    # ------------------------------------------------------------------
    def set_document_status(
        self, workspace_id: str, document_id: str, status: str,
    ) -> Optional[Document]:
        """Change a KB entry's approval status and record the transition."""
        if status not in APPROVAL_STATUSES:
            raise ValueError(status)
        doc = self.get_document(workspace_id, document_id)
        if doc is None:
            return None
        previous = doc.approval_status
        doc.approval_status = status
        doc.updated_at = _now()
        if status == APPROVAL_APPROVED:
            doc.approved_at = doc.updated_at
            event, verb = EVENT_DOCUMENT_APPROVED, "approved"
        elif status == APPROVAL_ARCHIVED:
            event, verb = EVENT_DOCUMENT_ARCHIVED, "archived"
        else:  # draft
            doc.approved_at = None
            event, verb = EVENT_DOCUMENT_DRAFTED, "moved back to draft"
        # Only record an activity when the status actually changed.
        if status != previous:
            self._record(workspace_id, event,
                         f"KB entry '{doc.title}' {verb}",
                         metadata={"document_id": doc.id, "document_title": doc.title,
                                   "from_status": previous, "to_status": status})
        return doc

    # ------------------------------------------------------------------
    # context packages -- approved knowledge bundled with an integrity hash
    # ------------------------------------------------------------------
    def list_context_packages(self, workspace_id: str) -> list[ContextPackage]:
        """Packages for a single workspace, newest-first."""
        scoped = [p for p in self._packages.values() if p.workspace_id == workspace_id]
        scoped.sort(key=lambda p: p.created_at, reverse=True)
        return scoped

    def create_context_package(
        self, workspace_id: str, name: str, entry_ids: list[str],
    ) -> ContextPackage:
        """Bundle approved KB entries into a hash-verified context package.

        Enforces workspace isolation (entries must belong to this workspace) and
        the approval constraint (every entry must be ``approved``).
        """
        ws = self._workspaces.get(workspace_id)
        if ws is None:
            raise KeyError(workspace_id)

        entries: list[Document] = []
        missing: list[str] = []
        for entry_id in entry_ids:
            doc = self.get_document(workspace_id, entry_id)
            if doc is None:
                missing.append(entry_id)
            else:
                entries.append(doc)
        if missing:
            raise KeyError(missing)

        not_approved = [e.id for e in entries if e.approval_status != APPROVAL_APPROVED]
        if not_approved:
            raise ApprovalConstraintError(not_approved)

        package = ContextPackage(
            id=f"pkg-{next(self._pkg_counter)}",
            name=name,
            workspace_id=workspace_id,
            selected_entry_ids=[e.id for e in entries],
            created_at=_now(),
            # All selected entries are approved, so the package is approved.
            approval_status=APPROVAL_APPROVED,
            context_hash=compute_context_hash(entries),
            entry_titles=[e.title for e in entries],
        )
        self._packages[package.id] = package
        self._record(workspace_id, EVENT_PACKAGE_CREATED,
                     f"Context Package '{package.name}' created",
                     metadata={"package_id": package.id, "package_name": package.name,
                               "entry_count": len(entries),
                               "context_hash": package.context_hash})
        return package

    # ------------------------------------------------------------------
    # activity / audit log -- scoped to a single workspace
    # ------------------------------------------------------------------
    def _record(self, workspace_id: str, event_type: str, description: str,
                metadata: Optional[dict] = None, ts: Optional[str] = None) -> WorkspaceActivity:
        activity = WorkspaceActivity(
            id=f"act-{next(self._act_counter)}",
            workspace_id=workspace_id,
            event_type=event_type,
            timestamp=ts or _now(),
            description=description,
            metadata=metadata or {},
        )
        self._activities.append(activity)
        return activity

    def list_activities(self, workspace_id: str, limit: int = 20) -> list[WorkspaceActivity]:
        """Return the latest ``limit`` activities for a single workspace.

        Results are strictly scoped by ``workspace_id`` and ordered newest-first.
        """
        scoped = [a for a in self._activities if a.workspace_id == workspace_id]
        scoped.sort(key=lambda a: a.timestamp, reverse=True)
        return scoped[: max(0, limit)]

    # ------------------------------------------------------------------
    # search -- strictly scoped to a single workspace
    # ------------------------------------------------------------------
    def search_documents(self, workspace_id: str, query: str) -> list[Document]:
        """Search documents within a single workspace.

        Isolation guarantee: the candidate set is filtered by ``workspace_id``
        BEFORE the text match is applied, so results can never leak across
        workspaces.
        """
        scoped = self.list_documents(workspace_id)
        q = (query or "").strip().lower()
        if not q:
            return scoped
        return [
            d for d in scoped
            if q in d.title.lower() or q in d.content.lower()
        ]


store = WorkspaceStore()
