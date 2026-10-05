from datetime import date
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__="users"

    id = Column(Integer, primary_key= True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "status IN ('unpaid', 'partially_paid', 'paid')",
            name="ck_invoices_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="unpaid")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_overdue(self) -> bool:
        return self.status != "paid" and self.due_date < date.today()