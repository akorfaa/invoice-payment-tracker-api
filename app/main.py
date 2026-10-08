from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.errors import register_error_handlers
from app.routers import auth, users, clients, invoices, payments

app = FastAPI(title="Invoice & Payment Tracker API")

register_error_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(payments.router)


@app.get("/")
def read_root():
    return {"message": "Invoice & Payment Tracker API is running"}


@app.get("/health/live")
def liveness_check():
    """Is the app process up? Deliberately does NOT touch the database.

    Render's health check uses this, so a database hiccup doesn't restart the app.
    """
    return {"status": "ok"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Deeper check: can we actually reach the database? Use this one by hand."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}