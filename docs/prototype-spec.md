# Improve The Existing Knowledge Base Product Specification

## Product Vision

Transform the existing single-tenant Knowledge Base into a multi-workspace system where users can organize, search, and manage documents across isolated workspaces. Each workspace acts as a logical boundary for document collections, enabling users to maintain separate knowledge domains (e.g., "Product Docs", "Legal", "Engineering") within a single application instance.

The workspace model provides organizational clarity, improved search precision, and scalability for users managing multiple document collections without the overhead of deploying separate instances.

## Target Users

**Primary User**: Knowledge workers, technical writers, and teams who manage multiple document collections and need logical separation between different knowledge domains.

**User Characteristics**:
- Currently using or evaluating the existing Knowledge Base system
- Managing 10-1000+ documents across multiple topics/projects
- Need to switch context between different document collections frequently
- Value search precision over broad recall
- Comfortable with web-based document management interfaces

**User Technical Level**: Intermediate - comfortable with web applications, understands concepts like "workspace" from tools like Slack, Notion, or Postman.

## Business Problem

### Current State Pain Points

1. **No Organizational Structure**: All documents exist in a flat namespace, making it difficult to manage documents from different projects, clients, or domains
2. **Search Noise**: Search results return matches from all documents, even when users only care about a specific subset
3. **No Isolation**: Cannot separate sensitive documents from general knowledge without deploying separate instances
4. **Poor Scalability**: As document count grows, the single-namespace model becomes unwieldy
5. **Context Switching Overhead**: Users managing multiple knowledge domains must mentally filter results or use external organization systems

### Desired State

Users can create multiple workspaces, assign documents to workspaces, and seamlessly switch between workspaces. Search and document operations are automatically scoped to the active workspace, providing clean separation and focused results.

## Core User Journeys

### Journey 1: First-Time Workspace Setup

**Actor**: Existing user with documents already in the system

**Flow**:
1. User logs into the Knowledge Base application
2. System detects existing documents without workspace assignment
3. System automatically creates a "Default" workspace and assigns all existing documents to it
4. User sees workspace selector in the UI showing "Default" as active
5. User accesses workspace management page
6. User creates new workspace "Engineering Docs"
7. User returns to main document view
8. User switches to "Engineering Docs" workspace (empty)
9. User uploads documents to "Engineering Docs" workspace

**Success Criteria**: Existing documents remain accessible, new workspaces can be created without data loss, workspace switching is intuitive.

### Journey 2: Multi-Workspace Document Management

**Actor**: User managing documents across multiple projects

**Flow**:
1. User has three workspaces: "Client A", "Client B", "Internal"
2. User selects "Client A" from workspace selector
3. User uploads 5 documents - all automatically assigned to "Client A"
4. User performs search for "contract terms"
5. Search results only show matches from "Client A" documents
6. User switches to "Client B" workspace
7. User performs same search for "contract terms"
8. Search results only show matches from "Client B" documents (different results)
9. User views workspace statistics showing document/chunk counts per workspace

**Success Criteria**: Documents are isolated by workspace, search respects workspace boundaries, switching is fast and clear.

### Journey 3: Workspace Lifecycle Management

**Actor**: User cleaning up old projects

**Flow**:
1. User accesses workspace management page
2. User sees list of all workspaces with statistics (doc count, chunk count, embedding count)
3. User identifies "Old Project 2023" workspace with 50 documents
4. User renames workspace to "Archive - Old Project 2023"
5. User later decides to delete the workspace
6. System prompts: "Delete workspace and all 50 documents? This cannot be undone."
7. User confirms deletion
8. System deletes workspace, all associated documents, chunks, and embeddings
9. User returns to main UI, workspace no longer appears in selector

**Success Criteria**: Workspace operations are clear, destructive actions have confirmation, cascading deletes work correctly.

### Journey 4: Workspace-Aware Search

**Actor**: User searching for specific information

**Flow**:
1. User has "Legal" workspace selected
2. User enters search query "privacy policy"
3. Search results display:
   - Workspace name: "Legal" (for context)
   - Document name: "GDPR_Compliance.pdf"
   - Relevant chunk with highlighting
   - Chunk metadata (page number, section)
4. User clicks result to view full document context
5. User switches to "Marketing" workspace
6. Same search returns different documents from Marketing workspace
7. User verifies workspace context is always visible in results

**Success Criteria**: Search results clearly indicate workspace context, no cross-workspace contamination, metadata is preserved.

## MVP Scope

### In Scope

**Data Model**:
- Workspace entity with id, name, created_at, updated_at
- Document-to-Workspace foreign key relationship
- Database migration to add workspace support
- Default workspace creation for existing documents

**Backend API Endpoints**:
- `POST /api/workspaces` - Create workspace
- `GET /api/workspaces` - List all workspaces
- `GET /api/workspaces/{id}` - Get workspace details
- `PUT /api/workspaces/{id}` - Rename workspace
- `DELETE /api/workspaces/{id}` - Delete workspace (cascade to documents)
- `GET /api/workspaces/{id}/stats` - Get workspace statistics
- Modify existing document endpoints to accept/require workspace_id
- Modify search endpoint to filter by workspace_id

**Frontend Components**:
- Workspace selector dropdown (persistent in header/nav)
- Workspace management page with CRUD operations
- Workspace statistics display
- Visual indicator of active workspace
- Updated search results to show workspace context
- Confirmation dialogs for destructive operations

**Migration & Compatibility**:
- Database migration script to add workspace_id column to documents table
- Migration script to create "Default" workspace
- Migration script to assign all existing documents to "Default" workspace
- Backward compatibility: system functions if workspace_id is null (assigns to Default)

**Docker & Deployment**:
- Updated Docker Compose configuration (if needed)
- Database migration runs automatically on container startup
- Environment variables for workspace defaults (optional)
- Verification that build process completes successfully

**UI/UX Improvements**:
- Clear workspace indicator always visible
- Smooth workspace switching without page reload
- Loading states during workspace operations
- Empty states for new workspaces
- Workspace name validation (non-empty, unique)

### Minimum Viable Features

1. **Workspace CRUD**: Create, read, update (rename), delete workspaces
2. **Document Assignment**: All documents belong to exactly one workspace
3. **Workspace Scoping**: Search and document lists filtered by active workspace
4. **Statistics**: Display doc/chunk/embedding counts per workspace
5. **Migration**: Existing documents automatically assigned to Default workspace
6. **UI Clarity**: Always-visible workspace selector and context indicators

## Out of Scope

### Explicitly Excluded from MVP

**Multi-User & Permissions**:
- User authentication/authorization
- Workspace sharing between users
- Role-based access control (admin, viewer, editor)
- Workspace ownership model
- User invitations to workspaces

**Advanced Workspace Features**:
- Workspace templates
- Workspace duplication/cloning
- Workspace archiving (soft delete)
- Workspace favorites/pinning
- Workspace color coding or icons
- Workspace descriptions or metadata
- Workspace tags or categories

**Cross-Workspace Operations**:
- Moving documents between workspaces
- Copying documents between workspaces
- Cross-workspace search (search all workspaces)
- Workspace merging
- Bulk document operations across workspaces

**Advanced Statistics**:
- Workspace usage analytics (search frequency, popular documents)
- Workspace size limits or quotas
- Storage usage per workspace
- Historical statistics or trends
- Export statistics to CSV/JSON

**Performance Optimizations**:
- Workspace-level caching strategies
- Lazy loading of workspace data
- Pagination of workspace lists (assume <100 workspaces)
- Optimistic UI updates

**Enterprise Features**:
- Workspace backup/restore
- Workspace import/export
- Audit logs for workspace operations
- Workspace-level API keys
- SSO integration
- Compliance features (data residency, retention policies)

**UI Polish**:
- Drag-and-drop workspace reordering
- Keyboard shortcuts for workspace switching
- Recent workspaces list
- Workspace search/filtering
- Mobile-responsive workspace management
- Dark mode for workspace UI

### Deferred to Future Iterations

- Document moving between workspaces (requires conflict resolution UX)
- Workspace-level settings (embedding model, chunk size)
- Workspace activity feeds
- Workspace collaboration features
- Advanced search filters (date range, document type, workspace combination)

## Data Concepts

### Core Entities

#### Workspace

**Purpose**: Logical container for organizing documents into isolated collections.

**Attributes**:
- `id` (UUID/Integer): Primary key, unique identifier
- `name` (String, max 255 chars): Human-readable workspace name, unique across system
- `created_at` (Timestamp): Workspace creation time
- `updated_at` (Timestamp): Last modification time

**Constraints**:
- Name must be non-empty and unique
- Name must be trimmed (no leading/trailing whitespace)
- Cannot delete workspace if it's the last remaining workspace
- System must always have at least one workspace

**Default Workspace**:
- Name: "Default" (or configurable via environment variable)
- Created automatically on first run or during migration
- Can be renamed but not deleted if it contains documents
- All existing documents assigned to Default during migration

#### Document (Modified)

**Purpose**: Represents an uploaded document with its content and metadata.

**New Attributes**:
- `workspace_id` (Foreign Key): References workspace.id, NOT NULL after migration

**Constraints**:
- Every document must belong to exactly one workspace
- Deleting a workspace cascades to delete all its documents
- Document names must be unique within a workspace (not globally)

**Migration Behavior**:
- Add workspace_id column (nullable initially)
- Create Default workspace
- Set all existing documents' workspace_id to Default workspace id
- Make workspace_id NOT NULL
- Add foreign key constraint with ON DELETE CASCADE

#### Chunk (Modified)

**Purpose**: Represents a text segment extracted from a document for embedding/search.

**Relationship Changes**:
- Indirectly associated with workspace through document relationship
- No direct workspace_id foreign key (normalized through document)

**Cascade Behavior**:
- Deleting workspace → deletes documents → deletes chunks

#### Embedding (Modified)

**Purpose**: Vector representation of a chunk for semantic search.

**Relationship Changes**:
- Indirectly associated with workspace through chunk → document relationship
- No direct workspace_id foreign key

**Cascade Behavior**:
- Deleting workspace → deletes documents → deletes chunks → deletes embeddings

### Derived Data

#### Workspace Statistics

**Purpose**: Provide quick overview of workspace contents.

**Computed Attributes**:
- `total_documents` (Integer): Count of documents in workspace
- `total_chunks` (Integer): Count of chunks across all documents in workspace
- `total_embeddings` (Integer): Count of embeddings across all chunks in workspace
- `last_updated` (Timestamp): Most recent document update time in workspace

**Computation**:
- Calculated on-demand via SQL aggregation queries
- Not stored in database (derived data)
- Cached in-memory for performance (optional optimization)

**Query Pattern**:
```sql
SELECT 
  COUNT(DISTINCT d.id) as total_documents,
  COUNT(DISTINCT c.id) as total_chunks,
  COUNT(DISTINCT e.id) as total_embeddings,
  MAX(d.updated_at) as last_updated
FROM workspaces w
LEFT JOIN documents d ON d.workspace_id = w.id
LEFT JOIN chunks c ON c.document_id = d.id
LEFT JOIN embeddings e ON e.chunk_id = c.id
WHERE w.id = ?
```

### Data Relationships

```
Workspace (1) ──< (N) Document (1) ──< (N) Chunk (1) ──< (1) Embedding
```

**Cascade Rules**:
- DELETE Workspace → CASCADE DELETE Documents → CASCADE DELETE Chunks → CASCADE DELETE Embeddings
- UPDATE Workspace.id → CASCADE UPDATE Document.workspace_id (if using natural keys, not recommended)

**Referential Integrity**:
- All foreign keys enforced at database level
- Application layer validates workspace existence before document operations
- Orphaned documents not allowed (workspace_id NOT NULL)

### Data Migration Strategy

**Phase 1: Schema Addition**
1. Add `workspace_id` column to `documents` table (nullable)
2. Add index on `documents.workspace_id`

**Phase 2: Default Workspace Creation**
1. Check if any workspace exists
2. If no workspaces exist, create "Default" workspace
3. Record Default workspace ID

**Phase 3: Data Migration**
1. Update all documents with NULL workspace_id to Default workspace ID
2. Verify all documents have workspace_id assigned

**Phase 4: Schema Enforcement**
1. Alter `workspace_id` column to NOT NULL
2. Add foreign key constraint: `documents.workspace_id` → `workspaces.id` ON DELETE CASCADE

**Rollback Strategy**:
- Migration script should be idempotent (can run multiple times safely)
- Before Phase 4, migration can be rolled back by dropping workspace_id column
- After Phase 4, rollback requires data export/import

**Migration Verification**:
- Count documents before and after migration (should match)
- Verify all documents have workspace_id
- Verify Default workspace exists
- Test document retrieval still works

## Technical Assumptions

### Technology Stack

**Frontend**:
- Vue 3 with Composition API
- TypeScript for type safety
- Vite for build tooling
- Pinia or Vue 3 reactive state for workspace context management
- Existing component library (assumed to exist)

**Backend**:
- Python 3.10+
- FastAPI framework
- SQLAlchemy ORM for database operations
- Alembic for database migrations
- Pydantic for request/response validation

**Database**:
- PostgreSQL (assumed, based on embedding requirements)
- pgvector extension for vector similarity search (assumed existing)
- ACID compliance for workspace operations

**Infrastructure**:
