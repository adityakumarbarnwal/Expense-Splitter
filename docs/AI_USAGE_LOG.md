# AI Usage Log — Group Expense Splitter

> This log records all meaningful AI-assisted work during development of the Group Expense Splitter project.
> Maintained per DSC4141 course requirements.

---

## Log Format

Each entry contains:
- **Date**: When the AI assistance occurred
- **Task**: What was being worked on
- **AI Tool**: Which AI system was used
- **Purpose**: Why AI was used
- **Prompt/Approach**: What was asked
- **Output**: What was generated
- **Accepted**: What was used as-is
- **Modified**: What was changed and why
- **Verification**: How the output was verified
- **Final Result**: Outcome

---

## Development-Phase AI Usage

### Entry 001 — Project Initialization and Architecture

| Field | Detail |
|-------|--------|
| **Date** | 2026-09-22 |
| **Task** | Initial project setup — architecture design, implementation plan, project structure |
| **AI Tool** | Antigravity (Gemini Advanced) |
| **Purpose** | Accelerate initial project scaffold, generate implementation plan, create documentation structure |
| **Prompt/Approach** | Provided detailed project requirements and course methodology; asked AI to inspect repository, design architecture, and begin building the complete application |
| **Output** | Complete project structure, implementation plan, database schema design, API design, documentation files, backend skeleton (FastAPI + SQLAlchemy + Alembic), frontend skeleton (React + Vite + Tailwind) |
| **Accepted** | Project structure, documentation templates, database schema design, base configurations |
| **Modified** | Reviewed all generated code; verified model relationships, schema constraints, API endpoint design; adjusted rounding strategy from ROUND_HALF_EVEN to ROUND_HALF_UP after reviewing Indian currency norms |
| **Verification** | Ran application, verified endpoints via FastAPI docs at /docs, manually tested group creation and member addition flows |
| **Final Result** | Working Sprint 1 vertical slice: create group, add members, view group |

---

### Entry 002 — Expense Calculation Engine

| Field | Detail |
|-------|--------|
| **Date** | 2026-09-22 |
| **Task** | Implementing equal-split calculation with Decimal rounding |
| **AI Tool** | Antigravity (Gemini Advanced) |
| **Purpose** | Generate deterministic monetary calculation code |
| **Prompt/Approach** | Asked to implement expense_calculator.py using Python Decimal with ROUND_HALF_UP, with the last participant absorbing any rounding remainder |
| **Output** | `expense_calculator.py` with `calculate_equal_split()` function, comprehensive edge case handling |
| **Accepted** | Core algorithm structure, Decimal usage |
| **Modified** | Added explicit test for single-paisa rounding differences; added validation that amount > 0 |
| **Verification** | Ran Pytest test suite covering: equal split, rounding cases, single participant, zero amount rejection |
| **Final Result** | Fully tested, deterministic calculation engine |

---

### Entry 003 — AI Expense Parser (In-Product Feature)

| Field | Detail |
|-------|--------|
| **Date** | 2026-09-22 |
| **Task** | Implementing the Gemini-based natural-language expense parser |
| **AI Tool** | Antigravity (Gemini Advanced) — generating parser code |
| **Purpose** | Build the GenAI pipeline for natural-language expense entry |
| **Prompt/Approach** | Asked to implement expense_parser.py using google-generativeai SDK, with structured output, Pydantic validation, and explicit guardrails preventing LLM output from reaching database directly |
| **Output** | `expense_parser.py`, `prompt_builder.py`, `ai_validator.py` with full error handling |
| **Accepted** | Prompt structure, Pydantic schema design, error handling pattern |
| **Modified** | Strengthened system prompt to be more explicit about JSON-only output; added confidence field to allow partial extractions; added explicit group members list in context |
| **Verification** | Tested with: valid sentence, missing amount, unknown member name, intentionally broken LLM response (by mocking), LLM timeout simulation |
| **Final Result** | Working GenAI pipeline with full validation and graceful fallback |

---

### Entry 004 — MongoDB Migration + JWT Authentication (v2)

| Field | Detail |
|-------|--------|
| **Date** | 2026-09-26 |
| **Task** | Complete backend rewrite: SQLite→MongoDB, add JWT auth, user accounts, notifications, email |
| **AI Tool** | Antigravity (Gemini Advanced) |
| **Purpose** | Implement comprehensive requirements: MongoDB (mandatory), JWT auth with httpOnly cookies, email-based group membership, in-app notifications, profile management |
| **Prompt/Approach** | Provided full requirements document; AI audited existing codebase, identified SQLite→MongoDB discrepancy, designed and implemented complete new architecture |
| **Output** | New MongoDB document models (Pydantic), Motor async DB layer, JWT auth with bcrypt, 8 API route modules, notification service, email service, balance engine rewrite, 7 test cases |
| **Accepted** | MongoDB document schema design, Motor integration pattern, JWT cookie-based auth, notification event system |
| **Modified** | Fixed Motor async API (server_info vs admin.command), fixed bcrypt 5.x compatibility (passlib→direct bcrypt), fixed Gemini model name (2.0→3.8-flash) |
| **Verification** | - Registered user, logged in via API ✅<br>- Created group, verified member join ✅<br>- Created expense, verified share calculation ✅<br>- Tested Gemini AI: `success:true`, `amount:500`, `confidence:high` ✅<br>- 7/7 unit tests pass ✅ |
| **Final Result** | Fully working v2 backend with MongoDB Atlas, JWT auth, AI expense parsing |

---

### Entry 005 — Gemini AI Root Cause Diagnosis

| Field | Detail |
|-------|--------|
| **Date** | 2026-09-26 |
| **Task** | Diagnose actual root cause of "AI service is temporarily unavailable" error |
| **AI Tool** | Antigravity (Gemini Advanced) |
| **Purpose** | Find actual underlying exception, not the generic catch-all message |
| **Diagnosis Method** | Added `exc_info=True` to error logger; read backend logs after hitting AI endpoint |
| **Root Cause Found** | `google.api_core.exceptions.NotFound: 404 This model models/gemini-2.0-flash is no longer available. Please update your code to use models/gemini-3.8-flash` |
| **Fix Applied** | Updated `GEMINI_MODEL=gemini-3.8-flash` in `.env`, `.env.example`, and `config.py` defaults |
| **Verification** | Re-tested AI endpoint: `{"success":true,"result":{"description":"Pizza","amount":500.0,"confidence":"high"}}` |
| **Final Result** | AI endpoint fully operational |

---

## In-Product AI Usage (Application Runtime)

The application uses the **Google Gemini API** (`gemini-3.8-flash`) for:

1. **Natural-language expense parsing** — endpoint `POST /api/v1/groups/:id/expenses/parse-ai`
   - Input: Free-text expense description + group member context + current user name
   - Output: Structured JSON with description, amount, payer_name, participant_names, confidence
   - Guardrail: Output validated against actual group member names (case-insensitive match)
   - Guardrail: Invalid amounts are flagged with warnings
   - Guardrail: AI output NEVER writes to MongoDB — user confirms first
   - Guardrail: Financial share calculations done by Python code, not LLM

---

## AI Verification Protocol

For every AI-generated piece of code in this project:

1. **Read** — Every line of AI-generated code was read and understood
2. **Reason** — The logic was traced through manually for correctness
3. **Test** — Automated tests cover the behavior
4. **Run** — Tests were actually executed (not just written)
5. **Review** — Edge cases were explicitly checked

We do not blindly trust AI output, especially for financial calculations.
