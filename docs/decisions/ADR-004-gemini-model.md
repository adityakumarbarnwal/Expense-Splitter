# ADR-004: AI Model Selection — Google Gemini

**Status:** Accepted  
**Date:** 2026-09-22  
**Deciders:** Aditya Kumar Barnwal (Developer A), Partner (Developer B)

---

## Context

The GenAI feature (natural-language expense parsing) requires an LLM API. The model must:

1. Understand natural language descriptions of expenses
2. Return structured JSON output matching a defined schema
3. Be fast enough for interactive use (< 10 seconds)
4. Be available for free or low cost for student projects
5. Support structured output (to reduce parsing complexity)

## Options Considered

| Provider | Model | Structured Output | Free Tier | Speed | Quality |
|----------|-------|------------------|-----------|-------|---------|
| Google | `gemini-2.0-flash` | ✅ Native JSON mode | ✅ Generous | Fast | Good |
| Google | `gemini-1.5-pro` | ✅ | ✅ | Slower | Very Good |
| OpenAI | `gpt-4o-mini` | ✅ JSON mode | ❌ Paid | Fast | Good |
| OpenAI | `gpt-4o` | ✅ | ❌ Paid | Medium | Excellent |
| Anthropic | `claude-haiku` | Partial | ❌ Paid | Fast | Good |
| Local | Ollama + Llama3 | Partial | ✅ Free | Hardware-dependent | Variable |

## Decision

**Google Gemini API with `gemini-2.0-flash`**

Implementation uses the `google-generativeai` Python SDK with structured output via `response_mime_type="application/json"` and `response_schema`.

## Reasoning

1. **Free tier**: Google AI Studio offers a free tier sufficient for student project development and demonstration
2. **Native structured output**: Gemini supports `response_schema` parameter which returns validated JSON matching a defined schema — critical for our use case
3. **Speed**: `gemini-2.0-flash` is fast enough for interactive use
4. **Python SDK**: The `google-generativeai` Python package integrates naturally with our FastAPI backend
5. **No credit card required for API key**: Important for student projects

## Prompt Design Principles

1. System prompt explicitly specifies JSON-only output
2. Group members list provided in context (limits hallucination)
3. Model instructed to use `null` for fields it cannot extract
4. Model instructed **not to guess** member names
5. `confidence` field requested to flag uncertain extractions
6. Temperature set low (0.1) for deterministic parsing

## Fallback Strategy

If the Gemini API:
- Returns an error → UI shows error message and offers manual form
- Times out → UI shows timeout message and offers manual form  
- Returns malformed JSON → Caught by Pydantic, UI shows error
- Returns unknown member names → Application validates against group, returns validation error

The application **never crashes** due to AI failure.

## Consequences

**Positive:**
- Native JSON schema enforcement reduces parsing complexity
- Free tier enables zero-cost development and demonstration
- Well-documented Python SDK

**Negative:**
- Dependency on Google's infrastructure
- API key required (managed via `.env`)
- Rate limits on free tier

## Revisit When

- Free tier limits are exceeded
- A better-structured-output model becomes available
- The project moves to production with paying users (evaluate cost)

## AI Assistance

This decision involved consulting AI (Antigravity) on model capabilities. Final decision made by development team.
