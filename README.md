# Invoice & Payment Tracker API

**Tier:** 1 (Junior) — Project 1 of the portfolio roadmap
**Status:** In progress — Session 10 done (deployed and smoke-tested live; only the final README and write-up remain)

## Problem

Small businesses need a simple, reliable way to track who they've billed, how much is owed, and whether it's been paid. This is a real, common operations/fintech problem — most small business owners run this off a spreadsheet, which breaks down fast once they have more than a handful of clients.

This project builds the backend for that: a multi-user API where each business owner can manage their own clients, send them invoices, and record payments against those invoices.

## Approach

- Each registered **user** represents a business owner. Users sign up and log in with a password; the API issues a JWT (a signed token that proves who they are on every request after that, so they don't have to re-send their password each time).
- Users create **clients** — the people/companies they invoice.
- Users create **invoices** tied to a client: amount, description, due date, and a status (`unpaid`, `partially_paid`, `paid`, `overdue`).
- Users record **payments** against an invoice. An invoice's status updates automatically based on how much has been paid.
- **Authorization** is enforced everywhere: user A can never read, edit, or delete user B's clients, invoices, or payments — even if they guess the right ID. This is the single most important thing to get right and to prove with a test.
- **Input validation** on every write endpoint (Pydantic models) — amounts must be positive with at most 2 decimal places, an invoice's due date can't be before its issue date, no empty descriptions, etc.
- **Automated tests** (pytest) cover: registration, login, CRUD happy paths, validation failures, and — critically — the cross-user access-denial rule.
- **Deployed live** on Render (free tier) with a managed Postgres database, so the portfolio has a real working link, not just a GitHub repo.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language/framework | Python 3.11+, FastAPI | You already know FastAPI from MEST; this project deepens it rather than starting from zero |
| Database | PostgreSQL | Industry-standard relational DB; matches "real backend" expectations |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Lets you version-control schema changes like a real team would |
| Validation | Pydantic v2 | Ships with FastAPI; strict request/response schemas |
| Auth | JWT via `python-jose`, password hashing via `passlib[bcrypt]` | Industry-standard stateless auth pattern |
| Testing | Pytest + `httpx`/FastAPI `TestClient` | Standard Python API testing stack |
| Dev database | Neon.tech (free, cloud-hosted Postgres) | No admin rights on this machine, so Docker Desktop isn't an option — Neon gives a real Postgres instance with no local install |
| Deployment | Render (free tier), Railway as backup | Free, supports Postgres + a web service, good enough for a portfolio link |

**Note on constraints:** this project is being built on a machine without admin/installer rights, so anything needing an elevated-permission install — Docker Desktop being the main one — is worked around rather than used. See `BUILD_PLAN.md` for how Sessions 1 and 9 handle this (cloud Postgres instead of local Docker; the Dockerfile is validated by Render's cloud build rather than run locally). This is worth a line in the portfolio write-up — designing around a locked-down machine is a realistic constraint, not a shortcut.

## Container

The `Dockerfile` packages the API on `python:3.11-slim`, installs only the production packages from `requirements.txt`, runs as a non-root user and listens on `$PORT` (Render's convention, default 8000). `.dockerignore` keeps `.env`, `venv/`, tests and local database files out of the build.

Dependencies are split three ways: `requirements.in` (the packages I chose), `requirements.txt` (the full pinned production set, generated from a clean install of the `.in` file) and `requirements-dev.txt` (production plus pytest, pytest-cov and the local test database).

**Honest limitation:** this machine has no admin rights, so Docker can't be installed and the image has never been built locally. I verified the riskiest part another way (a clean environment with only the production packages imports the app, and a clean dev environment passes all 64 tests), and the real image build is performed by Render's cloud build.

## How to run

*(This section gets filled in as we build — it will include environment variable setup, the Neon connection string, how to run migrations, and how to run the test suite.)*

## What I'd improve with more time

*(Filled in at the end of the project. Likely candidates: refresh tokens instead of long-lived access tokens, pagination on list endpoints, rate limiting, richer reporting/export, multi-currency support.)*

## Project links

- Live API: https://invoice-payment-tracker-api.onrender.com  *(free tier: after 15 minutes idle it sleeps, so the first request can take about a minute)*
- API docs (Swagger UI): https://invoice-payment-tracker-api.onrender.com/docs
