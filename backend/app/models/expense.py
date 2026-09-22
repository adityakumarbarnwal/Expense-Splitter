"""
Expense and ExpenseParticipant SQLAlchemy models.

Expense: A shared cost paid by one member on behalf of participants.
ExpenseParticipant: Links an expense to a participant with their calculated share.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Expense(Base):
    """A shared expense within a group."""

    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    # Use Numeric(12, 2) — stores exact decimal values
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="expenses")  # type: ignore[name-defined]
    payer: Mapped["Member"] = relationship(  # type: ignore[name-defined]
        "Member", back_populates="paid_expenses", foreign_keys=[payer_id]
    )
    participants: Mapped[list["ExpenseParticipant"]] = relationship(
        "ExpenseParticipant", back_populates="expense", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Expense id={self.id} description={self.description!r} amount={self.amount}>"


class ExpenseParticipant(Base):
    """Links a member to an expense with their calculated share amount."""

    __tablename__ = "expense_participants"
    __table_args__ = (
        UniqueConstraint("expense_id", "member_id", name="uq_expense_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    expense_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False
    )
    # The calculated share amount for this participant (Decimal)
    share: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    expense: Mapped["Expense"] = relationship("Expense", back_populates="participants")
    member: Mapped["Member"] = relationship(  # type: ignore[name-defined]
        "Member", back_populates="expense_participations"
    )

    def __repr__(self) -> str:
        return f"<ExpenseParticipant expense_id={self.expense_id} member_id={self.member_id} share={self.share}>"
