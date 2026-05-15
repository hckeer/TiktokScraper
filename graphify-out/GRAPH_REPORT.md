# Graph Report - .  (2026-05-15)

## Corpus Check
- Corpus is ~8,341 words - fits in a single context window. You may not need a graph.

## Summary
- 228 nodes · 278 edges · 15 communities detected
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 39 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Extractor Data Models|Extractor Data Models]]
- [[_COMMUNITY_BulletProof DataStore Operations|BulletProof DataStore Operations]]
- [[_COMMUNITY_Extractor Core Logic|Extractor Core Logic]]
- [[_COMMUNITY_Temporal Activities|Temporal Activities]]
- [[_COMMUNITY_Backend App & Export|Backend App & Export]]
- [[_COMMUNITY_Frontend UI Components|Frontend UI Components]]
- [[_COMMUNITY_Backend Routing Layer|Backend Routing Layer]]
- [[_COMMUNITY_Google Sheets Integration|Google Sheets Integration]]
- [[_COMMUNITY_Google Sheets Manager|Google Sheets Manager]]
- [[_COMMUNITY_Temporal Workflows|Temporal Workflows]]
- [[_COMMUNITY_Configuration System|Configuration System]]
- [[_COMMUNITY_Frontend Styling|Frontend Styling]]
- [[_COMMUNITY_Supabase Query|Supabase Query]]
- [[_COMMUNITY_Next.js Config Files|Next.js Config Files]]
- [[_COMMUNITY_Session Start Request|Session Start Request]]

## God Nodes (most connected - your core abstractions)
1. `BulletproofDataStore` - 15 edges
2. `BulletproofDataStore` - 14 edges
3. `stream_and_extract()` - 11 edges
4. `WebSocket /ws/{session_id} handler` - 8 edges
5. `main()` - 7 edges
6. `POST /api/sessions endpoint` - 7 edges
7. `UserRecord` - 6 edges
8. `GoogleSheetsManager` - 6 edges
9. `start_session()` - 6 edges
10. `Supabase client singleton` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Chrome extension popup UI` --semantically_similar_to--> `Home page - session creation form`  [INFERRED] [semantically similar]
  tiktok-extension/popup.html → frontend/app/page.tsx
- `stream_and_extract()` --calls--> `PhoneExtractor - Nepali phone number extraction`  [EXTRACTED]
  /home/hckeer/work/glm5.1tests/backend/temporal/activities.py → docs/extractor-api-notes.md
- `Extractor API design notes` --rationale_for--> `stream_and_extract()`  [INFERRED]
  docs/extractor-api-notes.md → /home/hckeer/work/glm5.1tests/backend/temporal/activities.py
- `test()` --calls--> `WebSocket /ws/{session_id} handler`  [INFERRED]
  /home/hckeer/work/glm5.1tests/test_ws.py → backend/routers/ws.py
- `CommentData` --semantically_similar_to--> `CommentData dataclass (backend)`  [EXTRACTED] [semantically similar]
  /home/hckeer/work/glm5.1tests/script.py → backend/extractor/extractor.py

## Communities

### Community 0 - "Extractor Data Models"
Cohesion: 0.07
Nodes (20): BulletproofDataStore class (backend), CommentData dataclass (backend), UserRecord dataclass (backend), BulletproofDataStore, CommentData, from_dict(), Single comment record, Aggregated data for a commenter (+12 more)

### Community 1 - "BulletProof DataStore Operations"
Cohesion: 0.08
Nodes (17): BulletproofDataStore, CommentData, from_dict(), Single comment record, Aggregated data for a commenter, Zero-loss data storage with:     - Async write-through queue     - Immediate dis, Load existing data and recover any pending writes, Load records from disk (+9 more)

### Community 2 - "Extractor Core Logic"
Cohesion: 0.08
Nodes (22): BaseModel, Enum, Config, extract(), Config dataclass (backend), PhoneExtractor class (backend), UserStatus enum (backend), PhoneExtractor (+14 more)

### Community 3 - "Temporal Activities"
Cohesion: 0.1
Nodes (21): connect_to_tiktok_live(), export_csv_activity(), export_excel_activity(), Streams comments, extracts numbers, and publishes to Redis, stream_and_extract(), update_session_status(), Extractor API design notes, SessionPage() (+13 more)

### Community 4 - "Backend App & Export"
Cohesion: 0.13
Nodes (20): Settings pydantic BaseSettings, FastAPI app instance, GET /api/sessions/{id}/export/csv endpoint, GET /api/sessions/{id}/export/excel endpoint, Export APIRouter, GET /api/sessions/{session_id} endpoint, Sessions APIRouter, POST /api/sessions endpoint (+12 more)

### Community 5 - "Frontend UI Components"
Cohesion: 0.13
Nodes (10): Home page - session creation form, Badge UI component, Badge(), Button UI component, cn(), Input UI component, Python dependencies, Chrome extension popup UI (+2 more)

### Community 6 - "Backend Routing Layer"
Cohesion: 0.22
Nodes (5): export_csv(), get_session(), start_session(), get_temporal_client(), websocket_endpoint()

### Community 7 - "Google Sheets Integration"
Cohesion: 0.29
Nodes (5): GoogleSheetsManager class (backend), GoogleSheetsManager, Manages Google Sheets sync with:     - Auto sheet creation     - Incremental upd, Initialize Google Sheets connection, Create or open the spreadsheet

### Community 8 - "Google Sheets Manager"
Cohesion: 0.33
Nodes (4): GoogleSheetsManager, Manages Google Sheets sync with:     - Auto sheet creation     - Incremental upd, Initialize Google Sheets connection, Create or open the spreadsheet

### Community 9 - "Temporal Workflows"
Cohesion: 0.33
Nodes (2): ExtractionWorkflow, run()

### Community 10 - "Configuration System"
Cohesion: 0.5
Nodes (3): BaseSettings, Config, Settings

### Community 12 - "Frontend Styling"
Cohesion: 0.67
Nodes (3): Root layout with font configuration, PostCSS configuration, Tailwind CSS configuration

### Community 15 - "Supabase Query"
Cohesion: 1.0
Nodes (2): Backend Supabase query script, Root-level Supabase query script

### Community 16 - "Next.js Config Files"
Cohesion: 1.0
Nodes (2): Next.js config (standalone output), Next.js config (empty)

### Community 27 - "Session Start Request"
Cohesion: 1.0
Nodes (1): SessionStartRequest pydantic model

## Ambiguous Edges - Review These
- `Next.js config (standalone output)` → `Next.js config (empty)`  [AMBIGUOUS]
  frontend/next.config.js · relation: semantically_similar_to

## Knowledge Gaps
- **53 isolated node(s):** `Centralized configuration`, `Single comment record`, `Aggregated data for a commenter`, `Enhanced Nepali phone number extraction`, `Zero-loss data storage with:     - Async write-through queue     - Immediate dis` (+48 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Temporal Workflows`** (6 nodes): `workflows.py`, `ExtractionWorkflow`, `.__init__()`, `get_status()`, `run()`, `stop()`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Supabase Query`** (2 nodes): `Backend Supabase query script`, `Root-level Supabase query script`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Next.js Config Files`** (2 nodes): `Next.js config (standalone output)`, `Next.js config (empty)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Session Start Request`** (1 nodes): `SessionStartRequest pydantic model`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Next.js config (standalone output)` and `Next.js config (empty)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `stream_and_extract()` connect `Temporal Activities` to `Extractor Core Logic`, `Backend Routing Layer`?**
  _High betweenness centrality (0.351) - this node is a cross-community bridge._
- **Why does `extract()` connect `Extractor Core Logic` to `Temporal Activities`?**
  _High betweenness centrality (0.318) - this node is a cross-community bridge._
- **Why does `ExtractionWorkflow Temporal workflow` connect `Backend App & Export` to `Extractor Core Logic`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `stream_and_extract()` (e.g. with `start_session()` and `publish_event()`) actually correct?**
  _`stream_and_extract()` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WebSocket /ws/{session_id} handler` (e.g. with `test_e2e()` and `test_e2e()`) actually correct?**
  _`WebSocket /ws/{session_id} handler` has 5 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Centralized configuration`, `Single comment record`, `Aggregated data for a commenter` to the rest of the system?**
  _53 weakly-connected nodes found - possible documentation gaps or missing edges._