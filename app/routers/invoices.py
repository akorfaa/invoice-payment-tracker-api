from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.dependencies import get_current_user

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _get_owned_client(db: Session, client_id: int, user: models.User) -> models.Client:
    client = (
        db.query(models.Client)
        .filter(models.Client.id == client_id, models.Client.owner_id == user.id)
        .first()
    )
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


def _get_owned_invoice(db: Session, invoice_id: int, user: models.User) -> models.Invoice:
    invoice = (
        db.query(models.Invoice)
        .join(models.Client, models.Invoice.client_id == models.Client.id)
        .filter(models.Invoice.id == invoice_id, models.Client.owner_id == user.id)
        .first()
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("/", response_model=schemas.InvoiceOut, status_code=201)
def create_invoice(
    invoice_in: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_client(db, invoice_in.client_id, current_user)
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
    return _get_owned_invoice(db, invoice_id, current_user)


@router.put("/{invoice_id}", response_model=schemas.InvoiceOut)
def update_invoice(
    invoice_id: int,
    invoice_in: schemas.InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = _get_owned_invoice(db, invoice_id, current_user)

    updates = invoice_in.model_dump(exclude_unset=True)
    if any(value is None for value in updates.values()):
        raise HTTPException(status_code=422, detail="Fields cannot be null")
    if updates.get("due_date", invoice.due_date) < invoice.issue_date:
        raise HTTPException(status_code=422, detail="due_date cannot be before issue_date")

    for field, value in updates.items():
        setattr(invoice, field, value)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    invoice = _get_owned_invoice(db, invoice_id, current_user)
    db.delete(invoice)
    db.commit()
    return None