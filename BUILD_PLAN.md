# Build Plan — Invoice & Payment Tracker API

Each session below is sized for 30–90 minutes. Don't try to do two sessions back to back without a break — this is meant to fit into spare time, not become a marathon.

When we sit down to actually do a session, I'll give you full numbered, copy-pasteable steps for just that session — this document is the map, not the turn-by-turn directions. Check off sessions as we finish them and update `_docs/progress-log.md` at the end of each one.

> **Environment note (added after Session 0):** This machine doesn't have admin rights, so Docker Desktop — and anything else needing an elevated-permission installer — is off the table. Sessions 1 and 9 below are adjusted to work around this: a free cloud Postgres database instead of a local Docker database, and the Dockerfile gets validated by Render's cloud build in Session 10 instead of by running Docker locally.

---

### Session 0 — Project skeleton & tooling (30–45 min)
**Goal:** A FastAPI app that runs locally and returns a "hello world" response, inside a proper Python project with git tracking it.
**Why it matters:** Every real project starts with a clean, reproducible setup — virtual environment, dependency list, `.gitignore`, git repo. Skipping this is the #1 reason side projects get abandoned or become unreproducible later.
**Covers:** virtual environment, `pip`/`requirements.txt`, FastAPI app skeleton, `uvicorn` dev server, git init + first commit, `.gitignore`.

- [x] Done

### Session 1 — Postgres connection, no local Docker (45–60 min)
**Goal:** A free, cloud-hosted Postgres database (via Neon.tech) that your local FastAPI app connects to over the network, using SQLAlchemy.
**Why it matters:** This is the first "real infrastructure" piece — most tutorials use SQLite, but Postgres is what you'll actually be judged on for a backend role. Normally teams run Postgres locally in Docker so dev doesn't depend on the internet, but that needs Docker Desktop, which needs admin rights you don't have here. A free cloud Postgres instance is the workaround — same SQL, same SQLAlchemy code, just reached over a connection string instead of `localhost`. It's also a genuinely common real-world setup, not just a workaround.
**Covers:** Neon.tech account + free project (no install, no credit card), keeping the connection string out of git via `.env` + `python-dotenv`, SQLAlchemy engine/session setup, a `/health` endpoint that proves the DB connection actually works.

- [ ] Not started

### Session 2 — User model, registration, password hashing (45–60 min)
**Goal:** A `User` table (via SQLAlchemy + Alembic migration) and a `POST /auth/register` endpoint that creates a user with a securely hashed password.
**Why it matters:** Introduces Alembic (schema migrations — how real teams change a database safely over time) and `passlib`/bcrypt (never store plain-text passwords — this is a baseline security expectation, not a nice-to-have).
**Covers:** Alembic setup, first migration, `User` model, Pydantic schemas for request/response, password hashing, first pytest test.

- [ ] Not started

### Session 3 — Login + JWT auth (45–75 min)
**Goal:** A `POST /auth/login` endpoint that verifies credentials and returns a JWT, plus a reusable `get_current_user` dependency that protects any endpoint you attach it to.
**Why it matters:** This is the auth mechanism the rest of the API leans on. Understanding *why* JWTs work (a signed token the server can verify without a database lookup) is a common interview question.
**Covers:** JWT encode/decode, login endpoint, `OAuth2PasswordBearer`/dependency injection for protected routes, tests for valid/invalid login and for accessing a protected route without a token.

- [ ] Not started

### Session 4 — Client CRUD (45–60 min)
**Goal:** Full create/read/update/delete endpoints for `Client`, scoped so a user only ever sees their own clients.
**Why it matters:** This is the first "real" resource and establishes the ownership pattern (`client.owner_id == current_user.id`) you'll reuse for every other resource. Get this pattern right once, reuse it everywhere.
**Covers:** `Client` model + migration, CRUD router, ownership-scoped queries, tests including "user B cannot see user A's client."

- [ ] Not started

### Session 5 — Invoice CRUD + status logic (60–90 min)
**Goal:** Full CRUD for `Invoice`, tied to a `Client`, with a status field (`unpaid`/`partially_paid`/`paid`/`overdue`).
**Why it matters:** Introduces a foreign-key relationship (invoice belongs to a client belongs to a user) and your first bit of business logic beyond plain CRUD — status isn't just user-set, it's derived.
**Covers:** `Invoice` model + migration, nested ownership checks (invoice → client → user), Pydantic validation (no negative amounts, due date rules), tests.

- [ ] Not started

### Session 6 — Payments + automatic status updates (45–75 min)
**Goal:** A `POST /invoices/{id}/payments` endpoint that records a payment and automatically recalculates the invoice's status (partial vs. fully paid vs. overpaid-rejected).
**Why it matters:** This is the most "product thinking" part of the project — translating a business rule ("an invoice is paid once payments sum to the invoice amount") into code and tests, rather than just exposing raw database fields.
**Covers:** `Payment` model + migration, status-recalculation logic, edge case handling (overpayment, payment on an already-paid invoice), tests for each case.

- [ ] Not started

### Session 7 — Error handling & validation hardening (30–60 min)
**Goal:** Consistent, sensible error responses across the whole API — proper 404s, 403s, 422s, with clear JSON error bodies instead of raw stack traces.
**Why it matters:** This is one of the clearest signals of production-mindedness vs. tutorial-mindedness. A senior-leaning reviewer will deliberately send bad input to see what comes back.
**Covers:** FastAPI exception handlers, custom exception classes, review pass over every endpoint for missing validation, tests for the error paths.

- [ ] Not started

### Session 8 — Test suite consolidation (45–75 min)
**Goal:** A test suite you'd be comfortable showing in an interview — organized, using fixtures (shared setup like "a logged-in test user"), and covering the cross-user access rule explicitly and thoroughly.
**Why it matters:** "Basic tests" from the roadmap means more than a couple of happy-path checks. This session is specifically about depth and organization, not new features.
**Covers:** pytest fixtures/conftest.py, a dedicated test file for the "can't touch another user's data" rule across every resource, a coverage check (`pytest-cov`) to spot untested paths.

- [ ] Not started

### Session 9 — Write the Dockerfile (30–45 min)
**Goal:** A working `Dockerfile` that packages the FastAPI app into a container image — built and actually run for real by Render during deployment (Session 10), since `docker build`/`docker run` locally need Docker Desktop, which needs admin rights.
**Why it matters:** Containerizing an app is a real, commonly-expected skill, and most cloud platforms (including Render) build your Dockerfile on their own servers — you don't need Docker installed on your machine to prove this. You're still writing real production infrastructure code; you just can't test-run the container locally, which we'll note honestly in the README's "what I'd improve with more time" section.
**Covers:** Dockerfile (base image, install dependencies, copy app code, expose port, start command), a `.dockerignore` file, and a short README note about the local-testing constraint.

- [ ] Not started

### Session 10 — Deploy to Render (45–75 min)
**Goal:** The API live on the internet with a real URL, backed by a managed Postgres instance, with migrations run against it.
**Why it matters:** A portfolio project that only "runs on my machine" is much weaker than one with a live link a recruiter or hiring manager can actually hit. This is the difference between "I built this" and "I shipped this."
**Covers:** Render account setup, environment variables/secrets, connecting to Render Postgres, running Alembic migrations against production, smoke-testing the live URL.

- [ ] Not started

### Session 11 — README, write-up, and wrap-up (30–45 min)
**Goal:** Finished README (how to run, what you'd improve), a short LinkedIn/portfolio write-up framed around the decisions you made (why JWT, why Postgres, why the ownership-check pattern) rather than just "I built an API," and the roadmap status doc updated.
**Why it matters:** Per the project instructions — the write-up should show decision-making, since that's what differentiates a portfolio piece from a tutorial clone.
**Covers:** Final README pass, `_docs/progress-log.md` closing entry, `_docs/roadmap-status.md` update, drafting the write-up.

- [ ] Not started

---

## Rough time budget

11 sessions × ~45–75 min average ≈ **8–14 hours total**, spread across your spare time. That's a realistic estimate for a junior-level CRUD-with-auth project done properly (with tests and a real deployment) rather than rushed.

## Definition of done for this project

- [ ] All endpoints implemented and protected by JWT auth where required
- [ ] Ownership checks proven by tests (not just "trust me")
- [ ] Pytest suite passes, covers happy paths + validation errors + auth failures
- [ ] App connects successfully to the Neon Postgres database in dev, and the Dockerfile builds and runs successfully on Render
- [ ] Live, working deployment URL
- [ ] README complete (problem, approach, tech stack, how to run, what I'd improve)
- [ ] Short write-up drafted for LinkedIn/portfolio site
