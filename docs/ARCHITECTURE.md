# Application Architecture

## Stack

- Frontend: React + Vite + TypeScript
- Backend: FastAPI + SQLAlchemy 2
- Database: PostgreSQL 15+
- Migrations: Alembic
- Charts: Recharts, lazy-loaded on Dashboard
- Backend tests: pytest
- Frontend tests: Vitest + Testing Library

## Repository layout

```text
frontend/          React application
backend/           FastAPI application, migrations, tests
docs/              database and UI design references
DATABASE_DESIGN.md approved logical design
render.yaml        deployment blueprint (later phase)
```

## Runtime boundary

The browser talks only to the FastAPI service. FastAPI reads `DATABASE_URL`; the frontend never receives database credentials. All user-owned API operations include a UUID `user_id` scope and verify row ownership through database joins.

The browser stores only `{ version, userId }` under a versioned local-storage key. It does not store the full profile or secrets.

## Frontend boundaries

- Route-level screens are lazy-loaded.
- API calls with no dependency run in parallel.
- Feature components are defined at module scope.
- Dashboard chart code is loaded only when Dashboard is visited.
- Long histories and exercise lists use `content-visibility: auto`.
- Server data remains the source of truth; local state is limited to form drafts and active input state.

## Backend boundaries

- Routers handle HTTP concerns.
- Pydantic schemas validate request and response shapes.
- Services own recommendation and transaction workflows.
- Repository/query modules own SQLAlchemy statements and aggregate SQL.
- Alembic owns schema changes; application startup does not call `create_all` in production.
- Profile onboarding is one transaction across user, initial body record, and preferred-body-part rows.
- Plan generation is one transaction. It records `algorithm_version` as either an LLM-backed version such as `llm-openai:gpt-4.1-mini` or `rules-v1-fallback`.
- LLM generation attempts are audited in `llm_generations`; API failures or missing `OPENAI_API_KEY` automatically fall back to the deterministic rule-based planner.
