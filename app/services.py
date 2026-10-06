from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models


def get_owned_client(db: Session, client_id: int, user: models.User) -> models.Client:
    client = (
        db.query(models.Client)
        .filter(models.Client.id == client_id, models.Client.owner_id == user.id)
        .first()
    )
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def get_owned_invoice(
    db: Session, invoice_id: int, user: models.User, lock: bool = False
) -> models.Invoice:
    query = (
        db.query(models.Invoice)
        .join(models.Client, models.Invoice.client_id == models.Client.id)
        .filter(models.Invoice.id == invoice_id, models.Client.owner_id == user.id)
    )
    if lock:
        query = query.with_for_update(of=models.Invoice)
    invoice = query.first()
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def total_paid(db: Session, invoice_id: int) -> Decimal:
    total = (
        db.query(func.coalesce(func.sum(models.Payment.amount), 0))
        .filter(models.Payment.invoice_id == invoice_id)
        .scalar()
    )
    return Decimal(total)


def recalculate_invoice_status(db: Session, invoice: models.Invoice) -> None:
    paid = total_paid(db, invoice.id)
    if paid >= invoice.amount:
        invoice.status = "paid"
    elif paid > 0:
        invoice.status = "partially_paid"
    else:
        invoice.status = "unpaid"