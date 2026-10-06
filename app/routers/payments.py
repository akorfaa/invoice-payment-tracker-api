from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user
from app.services import get_owned_invoice, recalculate_invoice_status, total_paid

router = APIRouter(prefix="/invoices/{invoice_id}/payments", tags=["payments"])


@router.post("", response_model=schemas.PaymentOut, status_code=201)
def record_payment(
    invoice_id: int,
    payment_in: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = get_owned_invoice(db, invoice_id, current_user, lock=True)

    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="Invoice is already fully paid")
    if payment_in.paid_on < invoice.issue_date:
        raise HTTPException(status_code=422, detail="paid_on cannot be before the invoice issue date")

    balance = invoice.amount - total_paid(db, invoice.id)
    if payment_in.amount > balance:
        raise HTTPException(
            status_code=409,
            detail=f"Payment of {payment_in.amount} exceeds the outstanding balance of {balance}",
        )

    payment = models.Payment(invoice_id=invoice.id, **payment_in.model_dump())
    db.add(payment)
    db.flush()
    recalculate_invoice_status(db, invoice)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=List[schemas.PaymentOut])
def list_payments(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = get_owned_invoice(db, invoice_id, current_user)
    return (
        db.query(models.Payment)
        .filter(models.Payment.invoice_id == invoice.id)
        .order_by(models.Payment.id)
        .all()
    )


@router.delete("/{payment_id}", status_code=204)
def delete_payment(
    invoice_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = get_owned_invoice(db, invoice_id, current_user, lock=True)
    payment = (
        db.query(models.Payment)
        .filter(models.Payment.id == payment_id, models.Payment.invoice_id == invoice.id)
        .first()
    )
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    db.delete(payment)
    db.flush()
    recalculate_invoice_status(db, invoice)
    db.commit()
    return None