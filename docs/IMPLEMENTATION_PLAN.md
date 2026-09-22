# Group Expense Splitter — Implementation Plan

> **Living document** — updated after every sprint and every meaningful architectural decision.
> Last updated: 2026-09-22

---

## 1. Product Vision

A web-based group expense splitting application that enables small groups (friends, flatmates, travel companions, colleagues) to record shared expenses, calculate individual balances, and settle debts — enhanced by a natural-language GenAI interface so that users can describe expenses conversationally rather than filling out rigid forms.

The GenAI component is a genuine user-facing capability, not a development tool mention.

---

## 2. Goals

1. Build a complete, working, demonstrable MVP by end of Sprint 3.
2. Demonstrate responsible GenAI integration: LLM for understanding, application code for calculation.
3. Follow the Agile/Sprint methodology specified in DSC4141 course notes.
4. Produce clean, tested, well-documented code suitable for academic review.
5. Maintain a living implementation plan, AI usage log, and ADRs throughout.

---

## 3. Scope

### In Scope

- Group creation and member management
- Expense recording (manual form and natural-language AI input)
- Equal-split expense calculation with correct monetary rounding
- Net balance calculation (who owes whom)
- Settlement recording and tracking
- Expense history view
- Natural-language expense parsing via Gemini API
- AI interpretation confirmation UI
- REST API (JSON)
- SQLite database (development)
- Automated backend tests (Pytest)
- Basic frontend component tests (Vitest)
- Documentation: README, implementation plan, ADRs, AI usage log, sprint reports

### Out of Scope (MVP)

- User authentication / login system (all users are identified by name within a group for MVP)
- Push notifications
- Mobile app
- PostgreSQL (will be noted as a production upgrade path)
- Multi-currency support
- Percentage/custom splits (only equal split in MVP)
- Receipt OCR / photo upload
- Export to CSV/PDF
- Email notifications

---

## 4. Functional Requirements

| ID  | Requirement |
|-----|-------------|
| FR-01 | Users can create a named group |
| FR-02 | Users can add named members to a group |
| FR-03 | Users can view all members of a group |
| FR-04 | Users can add an expense with description, amount, payer, and participants |
| FR-05 | System splits expense equally among participants |
| FR-06 | System handles monetary rounding correctly (Decimal, round-half-up) |
| FR-07 | Users can view current net balances for all group members |
| FR-08 | System shows a clear "who owes whom" settlement suggestion |
| FR-09 | Users can record a settlement payment between two members |
| FR-10 | Users can view expense history for a group |
| FR-11 | Users can enter an expense in natural language |
| FR-12 | System uses Gemini LLM to parse natural-language expense input |
| FR-13 | System validates AI output before presenting to user |
| FR-14 | Users can review and confirm AI-interpreted expense before saving |
| FR-15 | Users can correct AI interpretation before saving |
| FR-16 | System handles LLM failure gracefully (shows error, allows manual entry) |

---

## 5. Non-Functional Requirements

| ID   | Requirement |
|------|-------------|
| NFR-01 | API responses < 500ms for all non-AI endpoints |
| NFR-02 | AI parsing endpoint < 10 seconds (LLM call) |
| NFR-03 | All financial calculations use Python `Decimal` |
| NFR-04 | API keys stored in environment variables, never in code |
| NFR-05 | LLM output never written directly to database |
| NFR-06 | Backend test coverage > 80% for business logic |
| NFR-07 | Application fails gracefully — no raw stack traces shown to users |
| NFR-08 | Responsive UI (desktop-first, usable on tablet) |

---

## 6. User Roles / Actors

For the MVP, there is a single actor: **Group Member**.

A Group Member can:
- Create groups
- Join/add members to groups
- Record expenses
- View balances
- Record settlements
- Use natural-language expense entry

> Note: Authentication (login/accounts) is out of scope for the MVP. Members are identified by name within a group. This is an intentional academic simplification, documented in ADR-001.

---

## 7. Product Backlog

### US-01 — Create Group

| Field | Value |
|-------|-------|
| **Story** | As a user, I want to create a named group so that I can start tracking shared expenses. |
| **Priority** | P1 — Must Have |
| **Dependencies** | None |
| **Acceptance Criteria** | 1. User can enter a group name. 2. System creates the group and returns a group ID. 3. Group appears in group list. 4. Empty group name is rejected. 5. Duplicate group name shows a warning (but is allowed for MVP). |
| **Status** | ✅ Done (Sprint 1) |

---

### US-02 — Add Members to Group

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to add named members to my group so that expenses can be shared among the right people. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-01 |
| **Acceptance Criteria** | 1. User can add a member by name to an existing group. 2. Duplicate member names within a group are rejected. 3. Empty member name is rejected. 4. Member list updates immediately after adding. |
| **Status** | ✅ Done (Sprint 1) |

---

### US-03 — View Group Members

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to view all members of my group. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-01, US-02 |
| **Acceptance Criteria** | 1. Group detail page shows all member names. 2. Member count is visible. 3. Works for groups with 1–20 members. |
| **Status** | ✅ Done (Sprint 1) |

---

### US-04 — Add Expense (Manual)

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to add a shared expense with description, amount, payer, and participants. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-01, US-02 |
| **Acceptance Criteria** | 1. User can fill in description, amount, payer (from member list), and participants. 2. All fields validated. 3. Amount must be positive. 4. Payer must be a group member. 5. Participants must be group members. 6. At least one participant required. 7. Expense saved to database. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-05 — Calculate Shares

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want the system to automatically calculate each participant's equal share. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-04 |
| **Acceptance Criteria** | 1. System divides amount equally among participants. 2. Rounding handled correctly (Decimal, last participant absorbs remainder). 3. Results deterministic — same input always produces same output. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-06 — View Balances

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to see the current net balance for every member so I know who owes money and who is owed. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-04, US-05 |
| **Acceptance Criteria** | 1. Balance page shows net balance for each member. 2. Positive = owed money. Negative = owes money. Zero = settled. 3. Balances update when expenses or settlements are added. 4. Balances calculated in Python, not by LLM. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-07 — Who Owes Whom (Settlement Suggestions)

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to see a clear list of who should pay whom and how much to settle all debts. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-06 |
| **Acceptance Criteria** | 1. System produces a minimal list of settlement transactions. 2. If all balanced, shows "All settled!". 3. Calculated deterministically. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-08 — Record Settlement

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to record when one member pays another so balances are updated. |
| **Priority** | P1 — Must Have |
| **Dependencies** | US-06 |
| **Acceptance Criteria** | 1. User can record a settlement with payer, receiver, and amount. 2. Both payer and receiver must be group members. 3. Amount must be positive. 4. Balance updates after settlement. 5. Settlement appears in history. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-09 — Expense History

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to view a list of all expenses and settlements in the group. |
| **Priority** | P2 — Should Have |
| **Dependencies** | US-04, US-08 |
| **Acceptance Criteria** | 1. Expense history shows description, amount, payer, participants, date. 2. Settlement history shows payer, receiver, amount, date. 3. Listed in reverse chronological order. |
| **Status** | ✅ Done (Sprint 2) |

---

### US-10 — Natural-Language Expense Entry

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to type an expense description in plain English and have the system extract the expense details. |
| **Priority** | P1 — Must Have (GenAI requirement) |
| **Dependencies** | US-02, US-04 |
| **Acceptance Criteria** | 1. User can type free text like "I paid 1200 for dinner for me, Rahul and Aman". 2. System calls Gemini API and extracts: description, amount, payer, participants. 3. Extracted data is validated against group members. 4. If extraction fails or LLM is unavailable, user is notified gracefully. |
| **Status** | ✅ Done (Sprint 3) |

---

### US-11 — AI Confirmation UI

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to review and confirm (or correct) the AI-interpreted expense before it is saved. |
| **Priority** | P1 — Must Have (GenAI requirement) |
| **Dependencies** | US-10 |
| **Acceptance Criteria** | 1. After AI parses input, a preview card shows the interpretation. 2. User can confirm → expense saved normally. 3. User can edit fields → corrected expense saved. 4. User can cancel → nothing saved. 5. The raw AI JSON is never directly saved — always goes through normal validation pipeline. |
| **Status** | ✅ Done (Sprint 3) |

---

### US-12 — AI Expense Summary (Optional)

| Field | Value |
|-------|-------|
| **Story** | As a group member, I want to see a natural-language summary of the group's expense activity. |
| **Priority** | P3 — Nice to Have |
| **Dependencies** | US-09, US-10 |
| **Acceptance Criteria** | 1. A "Summarize" button calls Gemini to generate a brief narrative summary. 2. Summary is displayed to user clearly labeled as AI-generated. 3. No financial data is written based on this summary. |
| **Status** | 🔲 Backlog |

---

## 8. Sprint Plan

### Sprint 1 — Foundation: Groups and Members ✅

**Goal:** A working web application where a user can create a group, add members, and view them.

**Vertical Slice:** Create Group → Add Members → View Group

**Stories:** US-01, US-02, US-03

**Tasks:**
- [x] Initialize Git repository and project structure
- [x] Set up FastAPI backend skeleton
- [x] Define SQLAlchemy models: Group, Member
- [x] Create Alembic migration for initial schema
- [x] Implement API endpoints: POST /groups, GET /groups, GET /groups/{id}, POST /groups/{id}/members, GET /groups/{id}/members
- [x] Write Pytest tests for group and member endpoints
- [x] Initialize React + Vite + TailwindCSS frontend
- [x] Build GroupList page (view all groups, create group button)
- [x] Build GroupDetail page (view members, add member form)
- [x] Wire frontend to backend API
- [x] Write basic frontend component tests
- [x] Update documentation

**Expected Increment:** Runnable application demonstrating group and member management.

**Status:** ✅ Complete

---

### Sprint 2 — Core Expense Features ✅

**Goal:** Users can add expenses, see balances, and record settlements.

**Vertical Slice:** Add Expense → Calculate Shares → View Balances → Settlement

**Stories:** US-04, US-05, US-06, US-07, US-08, US-09

**Tasks:**
- [x] Define SQLAlchemy models: Expense, ExpenseParticipant, Settlement
- [x] Implement equal-split calculation with Decimal rounding
- [x] Implement balance calculation engine
- [x] Implement settlement suggestion algorithm (minimize transactions)
- [x] API endpoints: POST /expenses, GET /groups/{id}/expenses, GET /groups/{id}/balances, GET /groups/{id}/settlements-needed, POST /groups/{id}/settlements
- [x] Write Pytest tests for calculation engine (unit) and API (integration)
- [x] Build AddExpense form (React)
- [x] Build BalanceSummary component
- [x] Build SettlementList component
- [x] Build ExpenseHistory page
- [x] End-to-end test: Create group → Add members → Add expense → View balance → Record settlement
- [x] Update documentation

**Expected Increment:** Fully functional expense splitting without GenAI.

**Status:** ✅ Complete

---

### Sprint 3 — GenAI Natural-Language Expense Entry ✅

**Goal:** Users can describe an expense in natural language and have the AI extract the details.

**Vertical Slice:** NL Input → Gemini API → Structured Output → Validation → Confirmation UI → Normal Expense Pipeline

**Stories:** US-10, US-11

**Tasks:**
- [x] Create `backend/app/services/ai/` module
- [x] Implement `expense_parser.py`: prompt construction, Gemini call, response parsing
- [x] Implement `schemas.py`: Pydantic schema for AI output validation
- [x] Implement `prompts.py`: controlled system prompt
- [x] API endpoint: POST /ai/parse-expense
- [x] Application-level validation: check members exist in group
- [x] Graceful error handling: LLM failure, malformed output, ambiguous input
- [x] Write tests for AI service: valid input, missing amount, unknown member, LLM failure
- [x] Build NaturalLanguageInput component (React)
- [x] Build AIConfirmationCard component (review parsed result)
- [x] Integrate confirmation flow with normal expense creation
- [x] Update .env.example with GEMINI_API_KEY
- [x] Update AI_USAGE_LOG.md
- [x] Update documentation

**Expected Increment:** Complete GenAI pipeline demonstrable from UI.

**Status:** ✅ Complete

---

### Sprint 4 — Polish, Testing & Documentation 🔲

**Goal:** Production-quality code with complete test coverage and documentation.

**Tasks:**
- [ ] Review and improve test coverage
- [ ] Add error boundary components in React
- [ ] Improve loading states and error messages in UI
- [ ] Add input validation feedback in all forms
- [ ] Performance check all API endpoints
- [ ] Complete API documentation
- [ ] Final sprint retrospective
- [ ] Optional: US-12 AI Summary feature
- [ ] Prepare demo script

**Status:** 🔲 Planned

---

## 9. System Architecture

```
┌─────────────────────────────────────────────┐
│                   Browser                   │
│            React + Vite + Tailwind          │
│  Pages: Groups │ Expenses │ Balances │ AI   │
└───────────────────┬─────────────────────────┘
                    │ HTTP/REST (JSON)
                    │ localhost:8000
┌───────────────────▼─────────────────────────┐
│               FastAPI Backend               │
│  /api/v1/groups  /api/v1/expenses           │
│  /api/v1/balances  /api/v1/ai               │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │         Business Logic Layer        │    │
│  │  - expense_calculator.py            │    │
│  │  - balance_engine.py                │    │
│  │  - settlement_engine.py             │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │          AI Service Layer           │    │
│  │  - expense_parser.py                │    │
│  │  - prompt_builder.py                │    │
│  │  - ai_validator.py                  │    │
│  └────────────────────┬────────────────┘    │
│                        │                    │
│  ┌─────────────────────▼────────────────┐   │
│  │         SQLAlchemy ORM               │   │
│  │      Alembic Migrations              │   │
│  └─────────────────────┬────────────────┘   │
└────────────────────────┼────────────────────┘
                         │
           ┌─────────────▼────────────┐
           │    SQLite (dev.db)        │
           └──────────────────────────┘
                         
           External:
           ┌──────────────────────────┐
           │   Google Gemini API      │
           │   (AI service only)      │
           └──────────────────────────┘
```

---

## 10. Frontend Architecture

```
frontend/src/
├── components/
│   ├── groups/
│   │   ├── GroupCard.jsx
│   │   ├── GroupForm.jsx
│   │   └── MemberList.jsx
│   ├── expenses/
│   │   ├── ExpenseForm.jsx
│   │   ├── ExpenseList.jsx
│   │   └── ExpenseCard.jsx
│   ├── balances/
│   │   ├── BalanceSummary.jsx
│   │   └── SettlementSuggestions.jsx
│   ├── ai/
│   │   ├── NaturalLanguageInput.jsx
│   │   └── AIConfirmationCard.jsx
│   └── common/
│       ├── LoadingSpinner.jsx
│       ├── ErrorMessage.jsx
│       └── ConfirmDialog.jsx
├── pages/
│   ├── HomePage.jsx
│   ├── GroupDetailPage.jsx
│   ├── ExpensesPage.jsx
│   └── BalancesPage.jsx
├── services/
│   ├── api.js           # Axios client
│   ├── groupsApi.js
│   ├── expensesApi.js
│   ├── balancesApi.js
│   └── aiApi.js
├── hooks/
│   ├── useGroups.js
│   ├── useExpenses.js
│   └── useBalances.js
├── App.jsx
└── main.jsx
```

---

## 11. Backend Architecture

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory
│   ├── core/
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   └── dependencies.py  # DB session dep injection
│   ├── models/
│   │   ├── base.py
│   │   ├── group.py
│   │   ├── member.py
│   │   ├── expense.py
│   │   └── settlement.py
│   ├── schemas/
│   │   ├── group.py
│   │   ├── member.py
│   │   ├── expense.py
│   │   ├── settlement.py
│   │   └── ai_response.py
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py
│   │   │   ├── groups.py
│   │   │   ├── expenses.py
│   │   │   ├── balances.py
│   │   │   └── ai.py
│   ├── services/
│   │   ├── group_service.py
│   │   ├── expense_service.py
│   │   ├── balance_engine.py
│   │   ├── settlement_engine.py
│   │   └── ai/
│   │       ├── expense_parser.py
│   │       ├── prompt_builder.py
│   │       └── ai_validator.py
│   └── db/
│       ├── database.py
│       └── migrations/
│           └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_groups.py
│   ├── test_expenses.py
│   ├── test_balances.py
│   ├── test_settlements.py
│   └── test_ai_parser.py
├── alembic.ini
├── .env.example
└── requirements.txt
```

---

## 12. Database Design

```sql
-- Groups
CREATE TABLE groups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Members (named participants within a group)
CREATE TABLE members (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id   INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(group_id, name)   -- No duplicate names in same group
);

-- Expenses
CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    amount      NUMERIC(12, 2) NOT NULL,  -- Stored as Decimal
    payer_id    INTEGER NOT NULL REFERENCES members(id),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    note        TEXT
);

-- Expense Participants (who shares the expense)
CREATE TABLE expense_participants (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id  INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
    member_id   INTEGER NOT NULL REFERENCES members(id),
    share       NUMERIC(12, 2) NOT NULL,  -- Calculated share amount
    UNIQUE(expense_id, member_id)
);

-- Settlements
CREATE TABLE settlements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id    INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    payer_id    INTEGER NOT NULL REFERENCES members(id),   -- Who paid
    receiver_id INTEGER NOT NULL REFERENCES members(id),  -- Who received
    amount      NUMERIC(12, 2) NOT NULL,
    note        TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Rounding Strategy:** Python `Decimal` with `ROUND_HALF_UP`. For equal splits, the last participant absorbs any rounding remainder. Documented in ADR-003.

---

## 13. API Design

See [docs/api/api-design.md](api/api-design.md) for full specification.

### Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/groups | List all groups |
| POST | /api/v1/groups | Create a group |
| GET | /api/v1/groups/{id} | Get group details |
| GET | /api/v1/groups/{id}/members | List members |
| POST | /api/v1/groups/{id}/members | Add member |
| DELETE | /api/v1/groups/{id}/members/{mid} | Remove member |
| GET | /api/v1/groups/{id}/expenses | List expenses |
| POST | /api/v1/groups/{id}/expenses | Add expense |
| GET | /api/v1/groups/{id}/expenses/{eid} | Get expense detail |
| GET | /api/v1/groups/{id}/balances | Get net balances |
| GET | /api/v1/groups/{id}/settlements-needed | Get settlement suggestions |
| GET | /api/v1/groups/{id}/settlements | List settlement history |
| POST | /api/v1/groups/{id}/settlements | Record a settlement |
| POST | /api/v1/ai/parse-expense | Parse natural-language expense |

---

## 14. GenAI Architecture

### Pipeline

```
User types: "I paid 1200 for dinner for me, Rahul and Aman"
         ↓
POST /api/v1/ai/parse-expense
  { "text": "...", "group_id": 3, "current_member": "Aditya" }
         ↓
expense_parser.py
  1. Build prompt with group context (members list)
  2. Call Gemini API (gemini-2.0-flash)
  3. Request structured JSON output
  4. Parse and validate Pydantic schema
  5. Validate: members exist in group, amount > 0
         ↓
Return: { "description": "Dinner", "amount": 1200, "payer": "Aditya",
          "participants": ["Aditya","Rahul","Aman"], "confidence": "high" }
         ↓
AIConfirmationCard (React)
  - Shows parsed result
  - User edits if needed
  - User clicks Confirm
         ↓
POST /api/v1/groups/{id}/expenses  (normal expense pipeline)
         ↓
expense_service.py → validation → calculation → database
```

### Guardrails

- LLM output is **never** written directly to the database
- LLM output is **always** passed through Pydantic schema validation
- Member names are **validated against actual group members** before confirmation
- All financial calculations happen in Python (`Decimal`), **never in the LLM**
- If LLM fails, returns a structured error → UI falls back to manual form

### Prompt Design

The system prompt explicitly:
1. Tells the model to return **only valid JSON** matching the specified schema
2. Provides the **group members list** as context
3. Instructs the model to use `null` for any field it cannot confidently extract
4. Instructs the model **not to guess** member names — only use members from the list

---

## 15. Testing Strategy

### Backend (Pytest)

| Test Type | Files | Target Coverage |
|-----------|-------|-----------------|
| Unit — Calculation | `test_calculations.py` | 100% |
| Unit — Balance Engine | `test_balances.py` | 100% |
| Unit — Settlement Engine | `test_settlements.py` | 100% |
| Unit — AI Parser (mocked) | `test_ai_parser.py` | 90%+ |
| Integration — API | `test_groups.py`, `test_expenses.py` | 80%+ |

### Frontend (Vitest)

| Component | Tests |
|-----------|-------|
| GroupForm | Validation, submit |
| ExpenseForm | Validation, payer selection |
| AIConfirmationCard | Render, confirm, edit |
| BalanceSummary | Correct display |

### Manual Testing Checklist

- [ ] Create group
- [ ] Add members
- [ ] Add expense (manual)
- [ ] Verify balance calculation
- [ ] Record settlement
- [ ] Verify balance updates
- [ ] Natural-language expense entry
- [ ] Correct AI misinterpretation
- [ ] AI failure → graceful fallback

---

## 16. Security Considerations

| Risk | Mitigation |
|------|-----------|
| API key exposure | Stored in `.env`, never committed, `.env` in `.gitignore` |
| LLM prompt injection | Structured output schema + validated JSON parsing |
| Arbitrary DB access | SQLAlchemy ORM + parameterized queries only |
| Raw LLM output → DB | Explicit validation layer before any DB write |
| Cross-group data access | All queries filtered by `group_id` |

---

## 17. Deployment Plan

**Development:** SQLite + Uvicorn + Vite dev server (localhost)

**Demo:** Run both servers locally, demonstrate via browser

**Future Production Path (out of scope for MVP):**
- Backend: Railway / Render (FastAPI + Gunicorn)
- Database: PostgreSQL
- Frontend: Vercel / Netlify
- Secrets: Platform environment variables

---

## 18. Documentation Plan

| Document | Location | Updated When |
|----------|----------|--------------|
| Implementation Plan | `docs/IMPLEMENTATION_PLAN.md` | Every sprint |
| AI Usage Log | `docs/AI_USAGE_LOG.md` | Every AI-assisted task |
| ADR-001: No Auth in MVP | `docs/decisions/ADR-001-no-auth-mvp.md` | Initial |
| ADR-002: Technology Stack | `docs/decisions/ADR-002-tech-stack.md` | Initial |
| ADR-003: Rounding Strategy | `docs/decisions/ADR-003-decimal-rounding.md` | Sprint 2 |
| ADR-004: Gemini Model Choice | `docs/decisions/ADR-004-gemini-model.md` | Sprint 3 |
| API Design | `docs/api/api-design.md` | When API changes |
| Sprint 1 Report | `docs/sprints/sprint-1.md` | End of Sprint 1 |
| Sprint 2 Report | `docs/sprints/sprint-2.md` | End of Sprint 2 |
| Sprint 3 Report | `docs/sprints/sprint-3.md` | End of Sprint 3 |

---

## 19. AI Usage Plan

All meaningful GenAI use is logged in `docs/AI_USAGE_LOG.md`.

Categories:
1. **Development assistance** — AI used during project development (Antigravity/Claude/Gemini for code generation)
2. **In-product AI** — Gemini API calls made by the application itself

Both categories are logged with prompts, outputs, verification steps, and what was accepted/modified.

---

## 20. ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | No Authentication in MVP | Accepted |
| ADR-002 | Technology Stack Selection | Accepted |
| ADR-003 | Decimal Rounding Strategy | Accepted |
| ADR-004 | Gemini Model Selection | Accepted |

---

## 21. Definition of Done

A story is **Done** only when ALL of the following are satisfied:

- [ ] All acceptance criteria are met
- [ ] Code is implemented and functional
- [ ] Relevant unit tests written and passing
- [ ] API integration tests written and passing
- [ ] Code is reviewed (self-review for solo sections, peer review for pair sections)
- [ ] Feature integrated end-to-end (UI → API → DB)
- [ ] No known critical bugs
- [ ] Documentation updated (API docs, implementation plan if needed)
- [ ] Feature can be demonstrated in a live browser session
- [ ] AI usage logged if GenAI was used for this feature
