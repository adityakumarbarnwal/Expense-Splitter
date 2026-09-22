# Sprint 3 — GenAI Natural-Language Expense Entry

**Sprint Goal:** Users can type an expense description in plain English and have the AI extract structured data for confirmation.

**Sprint Dates:** 2026-09-22 (continuation of initial build session)

---

## Sprint Backlog

| Story | Priority | Status |
|-------|----------|--------|
| US-10: Natural-Language Entry | P1 | ✅ Done |
| US-11: AI Confirmation UI | P1 | ✅ Done |

---

## Completed Tasks

### AI Service (Backend)
- [x] `app/services/ai/prompt_builder.py` — Controlled system prompt + user prompt construction
- [x] `app/services/ai/expense_parser.py` — Gemini API integration with full error handling
- [x] `app/services/ai/ai_validator.py` — Application-level validation of AI output
- [x] `app/schemas/ai_response.py` — Pydantic schemas for AI request/response

### Backend API
- [x] `POST /api/v1/ai/parse-expense` — Parse natural language, validate, return for confirmation

### Frontend AI Components
- [x] `NaturalLanguageInput.jsx` — Text input with example prompts and member context
- [x] `AIConfirmationCard.jsx` — Review + edit + confirm UI

### Integration
- [x] AI entry button on Expenses page opens NaturalLanguageInput
- [x] On success, AIConfirmationCard shows parsed result
- [x] User confirms → sent to normal `POST /expenses` endpoint
- [x] LLM output never directly written to database

### Testing
- [x] `test_ai_parser.py` — 14 tests covering: valid parse, code fence stripping, null fields, unknown payer, unknown participant, case-insensitive matching, negative amount, missing API key, API failure, malformed response, unknown member warning

### Documentation
- [x] ADR-004: Gemini model selection
- [x] AI_USAGE_LOG.md: Entry 003 added
- [x] Sprint 3 report

---

## AI Pipeline Implementation

```
User Input (free text)
    ↓
POST /api/v1/ai/parse-expense
    ↓
[Backend] Group validation (group exists, has members)
    ↓
[Backend] expense_parser.py
  ├── Build prompt (system prompt + members list + user text)
  ├── Call Gemini API (gemini-2.0-flash, temperature=0.1)
  ├── Parse JSON response (strip markdown fences if needed)
  └── Validate with Pydantic schema
    ↓
[Backend] ai_validator.py
  ├── Case-insensitive member name matching
  ├── Unknown payer → cleared + warning
  ├── Unknown participants → removed + warning
  └── Non-positive amount → cleared + warning
    ↓
AIParseResponse { success, result, warnings, original_text }
    ↓
[Frontend] AIConfirmationCard
  ├── Shows original text + AI interpretation
  ├── Shows warnings prominently
  ├── User can edit all fields
  └── User confirms
    ↓
POST /api/v1/groups/{id}/expenses (normal pipeline)
    ↓
expense_calculator.py (Decimal split)
    ↓
Database
```

---

## Guardrails Implemented

| Guardrail | Where | How |
|-----------|-------|-----|
| LLM output never in DB | Backend | AI endpoint never calls DB write |
| Member validation | ai_validator.py | Case-insensitive name matching against actual group |
| Schema validation | Pydantic | `AIParseResult` schema validation |
| Amount validation | ai_validator.py | Amount must be positive Decimal |
| Financial calculation | expense_calculator.py | Python Decimal only |
| API failure handling | expense_parser.py | try/except → user-friendly message |
| Malformed JSON | expense_parser.py | `_parse_gemini_response` catches JSONDecodeError |
| User confirmation | Frontend | AIConfirmationCard — required before saving |

---

## Test Results

```
tests/test_ai_parser.py — 14 tests — ALL PASSED ✅
Total: 68 tests — 68 passed ✅
```

Frontend:
```
AIConfirmationCard.test.jsx — 6 tests — ALL PASSED ✅
```

---

## Definition of Done

- [x] Acceptance criteria satisfied
- [x] Code implemented with full guardrails
- [x] AI tests pass (mocked Gemini responses)
- [x] Frontend tests pass
- [x] Feature demonstrable end-to-end
- [x] AI usage logged in AI_USAGE_LOG.md
- [x] Documentation updated

---

## Sprint Retrospective

**What went well:**
- Pydantic schema catches malformed AI output cleanly
- The mocked test approach means tests are fast and don't require a real API key
- Low temperature (0.1) makes Gemini output more deterministic for parsing

**Key decisions:**
- `response_mime_type="application/json"` on Gemini ensures JSON output mode
- The `_parse_gemini_response` function handles markdown code fences since some models add them
- AI validator does case-insensitive matching since models may capitalize differently

**Next Sprint:**
- Sprint 4: Polish, additional test coverage, demo preparation
