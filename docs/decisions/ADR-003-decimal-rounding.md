# ADR-003: Decimal Rounding Strategy for Expense Splitting

**Status:** Accepted  
**Date:** 2026-09-22  
**Deciders:** Aditya Kumar Barnwal (Developer A), Partner (Developer B)

---

## Context

When splitting an expense equally among N participants, the amount often does not divide evenly. For example:

- ₹100 split among 3 people = ₹33.33... per person
- 3 × ₹33.33 = ₹99.99 ≠ ₹100

The system must handle this rounding case correctly and deterministically.

Two sub-problems:
1. **What type to use for money?** — Float, Decimal, or integer (paise)?
2. **How to handle the rounding remainder?** — Distribute, ignore, or assign to one participant?

## Options Considered

### Data Type

| Option | Analysis |
|--------|---------|
| Python `float` | Imprecise for decimal arithmetic (0.1 + 0.2 ≠ 0.3); unacceptable for financial use |
| Python `Decimal` | Exact decimal representation; configurable rounding modes; industry standard |
| Integer paise (1 ₹ = 100 paise) | Even more precise; more complex to display; suitable for high-volume systems |

### Rounding Mode

| Mode | Description |
|------|-------------|
| ROUND_HALF_UP | 0.5 rounds up (traditional; common expectation) |
| ROUND_HALF_EVEN | Banker's rounding (0.5 rounds to even; statistically unbiased) |
| ROUND_DOWN | Always truncate |
| ROUND_UP | Always round up |

### Remainder Assignment

| Option | Description |
|--------|-------------|
| Last participant absorbs remainder | Simple, deterministic |
| First participant absorbs remainder | Also simple |
| Largest-remainder method | Distributes fairly but complex |

## Decision

1. **Use Python `Decimal`** with 2 decimal places for all monetary values
2. **Use `ROUND_HALF_UP`** for per-share rounding
3. **Last participant absorbs rounding remainder** — their share is `total - sum_of_other_shares`

### Algorithm

```python
from decimal import Decimal, ROUND_HALF_UP

def calculate_equal_split(amount: Decimal, n_participants: int) -> list[Decimal]:
    share = (amount / n_participants).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shares = [share] * (n_participants - 1)
    # Last participant absorbs any rounding difference
    last_share = amount - sum(shares)
    shares.append(last_share)
    return shares
```

## Reasoning

1. **`Decimal` over `float`**: Non-negotiable for financial calculations. The precision requirement is absolute.
2. **`ROUND_HALF_UP`**: Most intuitive for users; consistent with everyday expectation; suitable for Indian rupee context.
3. **Last participant absorbs remainder**: The simplest deterministic approach. For academic purposes, the rounding difference is at most 1 paisa per participant, and the total always equals the original amount exactly. The "last" participant is ordered alphabetically for consistency.

## Consequences

**Positive:**
- Total always equals exactly the original amount (no money created or destroyed)
- Deterministic for the same input
- Simple to understand and verify
- Industry-standard approach for small-scale splitting apps

**Negative:**
- Last participant always bears the rounding burden (negligible at 1 paisa)
- Not perfectly "fair" for very small amounts with many participants

## Test Cases Defined

| Amount | Participants | Expected Shares |
|--------|-------------|-----------------|
| ₹100 | 3 | [₹33.33, ₹33.33, ₹33.34] |
| ₹100 | 2 | [₹50.00, ₹50.00] |
| ₹10 | 3 | [₹3.33, ₹3.33, ₹3.34] |
| ₹1 | 3 | [₹0.33, ₹0.33, ₹0.34] |

## Revisit When

- System needs to handle amounts with more than 2 decimal places
- Multi-currency requirements emerge (different decimal places per currency)
- Custom/weighted splits are implemented

## AI Assistance

The algorithm was generated with AI assistance (Antigravity). The rounding strategy decision was made by the development team. Tests were written and executed to verify correctness before accepting.
