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
| **AI Tool** | Antigravity (Claude Sonnet 4.6 Thinking) |
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
| **AI Tool** | Antigravity (Claude Sonnet 4.6 Thinking) |
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
| **AI Tool** | Antigravity (Claude Sonnet 4.6 Thinking) — generating parser code |
| **Purpose** | Build the GenAI pipeline for natural-language expense entry |
| **Prompt/Approach** | Asked to implement expense_parser.py using google-generativeai SDK, with structured output, Pydantic validation, and explicit guardrails preventing LLM output from reaching database directly |
| **Output** | `expense_parser.py`, `prompt_builder.py`, `ai_validator.py` with full error handling |
| **Accepted** | Prompt structure, Pydantic schema design, error handling pattern |
| **Modified** | Strengthened system prompt to be more explicit about JSON-only output; added confidence field to allow partial extractions; added explicit group members list in context |
| **Verification** | Tested with: valid sentence, missing amount, unknown member name, intentionally broken LLM response (by mocking), LLM timeout simulation |
| **Final Result** | Working GenAI pipeline with full validation and graceful fallback |

---

## In-Product AI Usage (Application Runtime)

The application uses the **Google Gemini API** (`gemini-2.0-flash`) for:

1. **Natural-language expense parsing** — endpoint `POST /api/v1/ai/parse-expense`
   - Input: Free-text expense description + group member context
   - Output: Structured JSON with description, amount, payer, participants
   - Guardrail: Output validated by Pydantic schema before any application use
   - Guardrail: Member names validated against actual group members
   - Guardrail: Financial calculations done by Python Decimal, not LLM

2. **Expense summary** (Sprint 4, optional) — endpoint `POST /api/v1/ai/summarize`
   - Input: Group expense data
   - Output: Natural-language narrative summary
   - Guardrail: No financial data written based on this output

---

## AI Verification Protocol

For every AI-generated piece of code in this project:

1. **Read** — Every line of AI-generated code was read and understood
2. **Reason** — The logic was traced through manually for correctness
3. **Test** — Automated tests cover the behavior
4. **Run** — Tests were actually executed (not just written)
5. **Review** — Edge cases were explicitly checked

We do not blindly trust AI output, especially for financial calculations.
