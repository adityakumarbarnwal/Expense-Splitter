# Sprint 1 — Foundation: Groups and Members

**Sprint Goal:** A working web application where users can create groups, add members, and view them.

**Sprint Dates:** 2026-09-22 (simulated single-session sprint for initial setup)

**Team:**
- Developer A: Aditya Kumar Barnwal
- Developer B: Partner

---

## Sprint Backlog

| Story | Priority | Status |
|-------|----------|--------|
| US-01: Create Group | P1 | ✅ Done |
| US-02: Add Members | P1 | ✅ Done |
| US-03: View Group Members | P1 | ✅ Done |

---

## Completed Tasks

### Backend
- [x] Initialized Git repository
- [x] Set up FastAPI backend project structure
- [x] Created SQLAlchemy models: `Group`, `Member`
- [x] Database auto-created on startup via `Base.metadata.create_all()`
- [x] Implemented `GET /api/v1/groups/` — list all groups
- [x] Implemented `POST /api/v1/groups/` — create group (with validation)
- [x] Implemented `GET /api/v1/groups/{id}` — get group + members
- [x] Implemented `DELETE /api/v1/groups/{id}` — delete group (cascade)
- [x] Implemented `GET /api/v1/groups/{id}/members` — list members
- [x] Implemented `POST /api/v1/groups/{id}/members` — add member (duplicate check)
- [x] Implemented `DELETE /api/v1/groups/{id}/members/{mid}` — remove member
- [x] CORS configured for React frontend

### Frontend
- [x] React + Vite + TailwindCSS project initialized
- [x] Global CSS with component classes
- [x] `Layout.jsx` — navigation bar
- [x] `HomePage.jsx` — list groups, create group, delete group
- [x] `GroupDetailPage.jsx` — view members, add member, remove member, navigation links

### Testing
- [x] Pytest conftest with isolated SQLite test database
- [x] `test_groups.py` — 17 tests covering all US-01/02/03 acceptance criteria
- [x] All 17 group/member tests passing

### Documentation
- [x] `README.md` created
- [x] `docs/IMPLEMENTATION_PLAN.md` created
- [x] `docs/AI_USAGE_LOG.md` — Entry 001 added
- [x] ADR-001, ADR-002, ADR-003, ADR-004 created
- [x] `.gitignore`, `.env.example` created

---

## Acceptance Criteria Verification

### US-01: Create Group
- [x] User can enter group name ✅
- [x] System creates group and returns group ID ✅
- [x] Group appears in list ✅
- [x] Empty name rejected ✅
- [x] Whitespace-only name rejected ✅

### US-02: Add Members
- [x] User can add member by name ✅
- [x] Duplicate names in same group rejected (409) ✅
- [x] Duplicate check is case-insensitive ✅
- [x] Empty name rejected ✅
- [x] Same name in different groups allowed ✅

### US-03: View Group Members
- [x] Group detail page shows all members ✅
- [x] Member count is visible ✅
- [x] Members listed alphabetically ✅

---

## Test Results

```
tests/test_groups.py — 17 tests — ALL PASSED ✅
Total: 68 tests — 68 passed ✅
```

---

## Definition of Done Checklist

- [x] All acceptance criteria satisfied
- [x] Code implemented and functional
- [x] Unit tests written and passing
- [x] API integration tests written and passing
- [x] Feature integrated end-to-end (UI → API → DB)
- [x] No known critical bugs
- [x] Documentation updated
- [x] Feature demonstrable in browser

---

## Sprint Retrospective

**What went well:**
- FastAPI + SQLAlchemy stack worked smoothly
- Pydantic validation caught input errors cleanly
- TailwindCSS accelerated UI development

**What needed fixing:**
- Initial test conftest used wrong engine — `no such table` error fixed by using `autouse` fixture
- Balance formula was incorrect (settlements_received/paid swapped) — fixed with clear documentation in ADR-003

**Technical Decisions Made:**
- Using `@pytest.fixture(autouse=True)` for DB table lifecycle — ensures test isolation
- Using `ORDER BY created_at DESC, id DESC` for deterministic ordering with same-second inserts

**Next Sprint:**
- Sprint 2: Expense creation, share calculation, balances, settlements
