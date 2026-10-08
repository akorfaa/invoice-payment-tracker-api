# Write-up: Invoice & Payment Tracker API

Two versions: a short LinkedIn post, and a longer case study for a portfolio site. Edit the wording so it sounds like you, and add one real thing you learned in your own words before posting.

---

## LinkedIn post

I just shipped my first portfolio project: an Invoice & Payment Tracker API, live and tested.

It's a multi-user backend where a small business can manage clients, invoices and payments. The invoice status (unpaid / partially paid / paid) and balance are calculated from the payments, so they can't drift out of sync.

The code was the easy part. The decisions were the real learning:

- Another user's invoice returns 404, not 403. A 403 confirms the record exists; a 404 reveals nothing.
- Money is stored as Decimal, never float, because floats can't represent 0.10 exactly.
- Tests run against a real Postgres, not SQLite, inside rolled-back transactions. The suite (66 tests, 97% coverage) runs in about 4 seconds. My first version took over 6 minutes because every test talked to a cloud database across the internet.
- My production database is on Neon because Render's free Postgres expires after 30 days.
- I have no admin rights on my laptop, so Docker was off the table. I used an embedded Postgres for tests and let Render's cloud build be the real test of the Dockerfile.

Stack: FastAPI, PostgreSQL, SQLAlchemy, Alembic, JWT, pytest, Docker, Render.

Live docs: https://invoice-payment-tracker-api.onrender.com/docs
Code: https://github.com/akorfaa/invoice-payment-tracker-api

Next up: a data project on insurance data, then an LLM tool.

#Python #FastAPI #BackendDevelopment #PostgreSQL #Fintech

---

## Portfolio case study

### The problem
Small businesses often track who owes them money in a spreadsheet. That works until there are many clients, partial payments and overdue invoices. I built the backend for a proper tool: a multi-user API where each owner manages their own clients, invoices and payments.

### What I built
A FastAPI + PostgreSQL REST API with JWT authentication, full CRUD for clients and invoices, and payments that automatically update invoice status. It is deployed on Render with a Neon database, has 66 automated tests at 97% coverage, and ships as a Docker image.

### Decisions that mattered

**Authorization through ownership, with 404s.** Every query that touches an invoice or payment is scoped to the logged-in user by joining invoice → client → user. If you ask for someone else's record, you get "not found", never "forbidden". I wrote a dedicated test suite where a second user attacks every endpoint with guessed IDs.

**Derived values, not stored ones.** `amount_paid`, `balance_due` and `is_overdue` are computed from the payments. Storing them would create two sources of truth that eventually disagree.

**Concurrency awareness.** Two payments arriving at the same moment could each pass the "does this exceed the balance?" check. Recording a payment locks the invoice row (`SELECT ... FOR UPDATE`). I haven't load-tested this, since my test setup uses one connection per test and cannot reproduce a real race, and I say so in the README.

**One error format.** Validation errors, conflicts, auth failures and unexpected crashes all return the same JSON shape. Database errors are translated into clean 409s so SQL never leaks to the client.

**Fast, honest tests.** My first test suite ran against the cloud database and took over six minutes, which meant I stopped running it. I switched to an embedded local Postgres, with each test wrapped in a transaction that rolls back. The suite now takes about 4 seconds, so I run it constantly.

**Working within a constraint.** My machine has no admin rights, so no Docker. I validated the Dockerfile by installing only the production dependencies in a clean environment and importing the app, then let Render's cloud build prove the image. I documented this limitation instead of hiding it.

**Hosting choices.** Render's free Postgres expires after 30 days, so the database lives on Neon. A cheap liveness endpoint (`/health/live`) is separate from the database health check, so a database blip doesn't cause a healthy app to be restarted.

### What I'd do next
Pagination, soft-deletes with an audit trail, rate limiting, CI that runs migrations, and a real concurrency test for the payment lock.

### Links
- Live docs: https://invoice-payment-tracker-api.onrender.com/docs
- Code: https://github.com/akorfaa/invoice-payment-tracker-api
