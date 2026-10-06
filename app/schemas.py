from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class ClientOut(ClientBase):
    id: int
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class InvoiceCreate(BaseModel):
    client_id: int
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    issue_date: date = Field(default_factory=date.today)
    due_date: date

    @model_validator(mode="after")
    def due_date_not_before_issue_date(self):
        if self.due_date < self.issue_date:
            raise ValueError("due_date cannot be before issue_date")
        return self


class InvoiceUpdate(BaseModel):
    amount: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: Optional[str] = Field(default=None, min_length=1, max_length=500)
    due_date: Optional[date] = None


class InvoiceOut(BaseModel):
    id: int
    client_id: int
    amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    description: str
    issue_date: date
    due_date: date
    status: str
    is_overdue: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


PaymentMethod = Literal["cash", "bank_transfer", "mobile_money", "card", "other"]


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    paid_on: date = Field(default_factory=date.today)
    method: Optional[PaymentMethod] = None
    reference: Optional[str] = Field(default=None, max_length=100)

    @field_validator("paid_on")
    @classmethod
    def paid_on_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("paid_on cannot be in the future")
        return value


class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    paid_on: date
    method: Optional[str]
    reference: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)