# Sprint 2 — Core Expense Features

**Sprint Goal:** Users can add expenses, see who owes what, and record settlements.

**Sprint Dates:** 2026-09-22 (continuation of initial build session)

---

## Sprint Backlog

| Story | Priority | Status |
|-------|----------|--------|
| US-04: Add Expense | P1 | ✅ Done |
| US-05: Calculate Shares | P1 | ✅ Done |
| US-06: View Balances | P1 | ✅ Done |
| US-07: Who Owes Whom | P1 | ✅ Done |
| US-08: Record Settlement | P1 | ✅ Done |
| US-09: Expense History | P2 | ✅ Done |

---

## Completed Tasks

### Business Logic
- [x] `expense_calculator.py` — Equal split using `Decimal` + `ROUND_HALF_UP`
- [x] `balance_engine.py` — Net balance calculation with settlement adjustments
- [x] `settlement_engine.py` — Greedy creditor-debtor matching algorithm

### Backend API
- [x] SQLAlchemy models: `Expense`, `ExpenseParticipant`, `Settlement`
- [x] `POST /api/v1/groups/{id}/expenses` — create expense with share calculation
- [x] `GET /api/v1/groups/{id}/expenses` — list expenses (newest first)
- [x] `DELETE /api/v1/groups/{id}/expenses/{eid}` — delete expense
- [x] `GET /api/v1/groups/{id}/balances` — net balances + settlement suggestions
- [x] `GET /api/v1/groups/{id}/settlements` — settlement history
- [x] `POST /api/v1/groups/{id}/settlements` — record settlement
- [x] All endpoints validate payer/participants belong to group

### Frontend
- [x] `ExpensesPage.jsx` — expense list, manual form, AI entry button
- [x] `BalancesPage.jsx` — net balances, settlement suggestions (with one-click record), history
- [x] Navigation between all pages

### Testing
- [x] `test_calculations.py` — 11 unit tests for expense calculator
- [x] `test_expenses.py` — 10 API integration tests
- [x] `test_balances.py` — 11 tests (unit + API) for balance and settlement engines

---

## Key Technical Decision: Balance Formula

Bug found and fixed during testing:

**Initial (wrong):**
```python
net = total_paid - total_owed + settlements_received - settlements_paid
```

**Corrected:**
```python
net = total_paid - total_owed + settlements_paid - settlements_received
```

**Reasoning:**
- `settlements_paid`: money you paid others → your debt is cleared → your net increases
- `settlements_received`: money you received → your outstanding credit is consumed → your net decreases

Verified with test case: Aditya pays ₹600 for [Aditya, Rahul], Rahul settles ₹300 → both net = 0.

---

## Test Results

```
tests/test_calculations.py — 11 tests — ALL PASSED ✅
tests/test_expenses.py — 10 tests — ALL PASSED ✅
tests/test_balances.py — 11 tests — ALL PASSED ✅
Total: 68 tests — 68 passed ✅
```

---

## Definition of Done

- [x] All acceptance criteria satisfied
- [x] Code implemented and functional
- [x] Unit and integration tests passing
- [x] Feature demonstrable end-to-end
- [x] Documentation updated

---

## Sprint Retrospective

**What went well:**
- `Decimal` arithmetic worked correctly for all rounding test cases
- Greedy settlement algorithm produces correct minimal transaction sets
- One-click settlement recording from suggestions is a nice UX touch

**Bug fixed:**
- Balance formula had `settlements_received - settlements_paid` reversed — caught by test `test_balances_settle_to_zero`

**Next Sprint:**
- Sprint 3: GenAI natural-language expense entry
