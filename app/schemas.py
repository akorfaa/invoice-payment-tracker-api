from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator

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
    description: str
    issue_date: date
    due_date: date
    status: str
    is_overdue: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)