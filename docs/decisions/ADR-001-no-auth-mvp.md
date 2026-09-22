# ADR-001: No User Authentication in MVP

**Status:** Accepted  
**Date:** 2026-09-22  
**Deciders:** Aditya Kumar Barnwal (Developer A), Partner (Developer B)

---

## Context

The Group Expense Splitter MVP needs to identify who paid an expense and who owes money. True user authentication (login, sessions, passwords) adds significant complexity:

- Backend: JWT token management, password hashing, session handling
- Frontend: Login/signup flows, protected routes, token storage
- Database: User credentials table, session management

This complexity would consume a significant portion of the sprint budget and is orthogonal to the core academic learning objectives of:
1. Building a GenAI application
2. Practicing Agile methodology
3. Demonstrating expense calculation and settlement logic

## Options Considered

### Option A: No authentication (name-based identification)
- Members are identified by name within a group
- Any user with the group link can access the group
- No passwords, sessions, or tokens

### Option B: Simple session-based auth
- Username + password
- Session cookies
- Protected routes

### Option C: OAuth (Google Sign-In)
- More realistic but adds external dependency
- Significant complexity for MVP

## Decision

**Option A — No authentication for MVP.**

Members are identified by their name within a group context. The group itself is accessed by its ID (URL-based).

## Reasoning

1. The core learning objectives are GenAI integration and Agile methodology — not auth systems
2. Removes ~2 weeks of scope, allowing full focus on core features
3. The application remains fully demonstrable and functional
4. The limitation is clearly documented and understood
5. Authentication can be added in a post-MVP phase without changing the core architecture

## Consequences

**Positive:**
- Significantly reduced scope and complexity
- Faster path to demonstrable MVP
- Focus on GenAI and expense logic

**Negative:**
- Not production-ready without auth
- Any user with the group URL can view/modify the group
- For academic demo context, this is acceptable

## Revisit When

- The application is being deployed for real use
- The course requires authentication features
- MVP is complete and scope allows adding auth

## AI Assistance

This decision was reached without AI — it's a deliberate academic scoping decision. Documented for transparency.
