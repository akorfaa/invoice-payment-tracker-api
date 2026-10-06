from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user
from app.services import (
    get_owned_client,
    get_owned_invoice,
    recalculate_invoice_status,
    total_paid,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post("/", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    invoice_in: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    get_owned_client(db, invoice_in.client_id, current_user)
    new_invoice = models.Invoice(**invoice_in.model_dump())
    db.add(new_invoice)
    db.commit()
    db.refresh(new_invoice)
    return new_invoice


@router.get("/", response_model=List[schemas.InvoiceOut])
def list_invoices(
    client_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = (
        db.query(models.Invoice)
        .join(models.Client, models.Invoice.client_id == models.Client.id)
        .filter(models.Client.owner_id == current_user.id)
        .options(selectinload(models.Invoice.payments))
    )
    if client_id is not None:
        query = query.filter(models.Invoice.client_id == client_id)
    return query.order_by(models.Invoice.id).all()


@router.get("/{invoice_id}", response_model=schemas.InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_owned_invoice(db, invoice_id, current_user)


@router.put("/{invoice_id}", response_model=schemas.InvoiceOut)
def update_invoice(
    invoice_id: int,
    invoice_in: schemas.InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = get_owned_invoice(db, invoice_id, current_user, lock=True)

    updates = invoice_in.model_dump(exclude_unset=True)
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Fields cannot be null")
    if updates.get("due_date", invoice.due_date) < invoice.issue_date:
        raise HTTPException(status_code=422, detail="due_date cannot be before issue_date")

    already_paid = total_paid(db, invoice.id)
    if "amount" in updates and updates["amount"] < already_paid:
        raise HTTPException(
            status_code=409,
            detail=f"Amount cannot be lower than the {already_paid} already paid",
        )

    for field, value in updates.items():
        setattr(invoice, field, value)
    recalculate_invoice_status(db, invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = get_owned_invoice(db, invoice_id, current_user)

    has_payments = (
        db.query(models.Payment).filter(models.Payment.invoice_id == invoice.id).first()
    )
    if has_payments:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an invoice that has payments. Delete the payments first.",
        )

    db.delete(invoice)
    db.commit()
    return None