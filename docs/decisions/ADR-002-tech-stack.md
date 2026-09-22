# ADR-002: Technology Stack Selection

**Status:** Accepted  
**Date:** 2026-09-22  
**Deciders:** Aditya Kumar Barnwal (Developer A), Partner (Developer B)

---

## Context

The project needs a full-stack web technology selection. The repository was empty. The course specifies no mandatory technology, but does specify REST API, database, and GenAI integration.

## Options Considered

### Backend

| Option | Pros | Cons |
|--------|------|------|
| FastAPI (Python) | Fast, async, automatic OpenAPI docs, Python ecosystem for AI | Requires ASGI server knowledge |
| Flask (Python) | Simple, familiar | Manual OpenAPI docs, less structured |
| Django (Python) | Batteries included, ORM | Heavier, more opinionated |
| Node.js + Express | Same language as frontend | Python better for AI/data |
| Node.js + NestJS | Structured | Heavier learning curve |

### Frontend

| Option | Pros | Cons |
|--------|------|------|
| React + Vite | Fast, widely used, rich ecosystem | JSX learning curve |
| Vue 3 | Simpler template syntax | Smaller ecosystem |
| Next.js | Full-stack option | More complex for simple API separation |
| Vanilla JS | No framework | Too slow for component-heavy UI |

### Database

| Option | Pros | Cons |
|--------|------|------|
| SQLite | Zero config, file-based, perfect for dev | Not for concurrent production use |
| PostgreSQL | Production-grade | Requires running server locally |
| MongoDB | Flexible schema | Relational data fits SQL better |

### AI Provider

| Option | Pros | Cons |
|--------|------|------|
| Google Gemini API | Free tier available, structured output support, project team familiarity | API key required |
| OpenAI GPT-4 | Widely documented | Paid, no free tier |
| Anthropic Claude | Good reasoning | Paid |
| Local LLM | No API cost | Setup complexity, hardware requirements |

## Decision

| Layer | Choice |
|-------|--------|
| Backend | **FastAPI** (Python 3.12) |
| ORM | **SQLAlchemy 2** + **Alembic** (migrations) |
| Database | **SQLite** (development), PostgreSQL-compatible for production |
| Frontend | **React 18** + **Vite** + **TailwindCSS** |
| AI Provider | **Google Gemini API** (`gemini-2.0-flash`) |
| Testing BE | **Pytest** + **HTTPX** (async test client) |
| Testing FE | **Vitest** + **React Testing Library** |

## Reasoning

1. **FastAPI**: Python is the natural choice for AI integration; FastAPI gives automatic OpenAPI documentation which supports our API design requirement; pydantic-based validation aligns with our structured output validation need
2. **SQLAlchemy + Alembic**: Industry-standard ORM with migration support, compatible with both SQLite (dev) and PostgreSQL (prod)
3. **SQLite**: Zero configuration; the application is designed for academic demonstration, not concurrent production use
4. **React + Vite**: Industry-standard frontend; Vite provides fast HMR; TailwindCSS enables rapid UI development
5. **Gemini API**: Free tier available for student projects; supports structured JSON output (important for our GenAI pipeline); `gemini-2.0-flash` is fast and sufficient for expense parsing

## Consequences

**Positive:**
- All chosen technologies are well-documented with large communities
- Python ecosystem makes AI service integration natural
- Automatic OpenAPI docs reduce API documentation effort
- TailwindCSS reduces CSS complexity

**Negative:**
- Two different languages (Python/JavaScript) require context switching
- SQLite not suitable for production multi-user deployment

## Revisit When

- Moving to production deployment (upgrade SQLite → PostgreSQL)
- Performance requirements change (consider async DB drivers)
- AI cost becomes a concern (consider switching providers or caching)

## AI Assistance

AI (Antigravity) was consulted on the technology selection. The final decision was made by the development team after reviewing the trade-offs. The decision aligns with the recommendations in the project brief.
