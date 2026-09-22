"""
Group and Member SQLAlchemy models.

Group: A named collection of people sharing expenses.
Member: A named participant within a group.
"""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Group(Base):
    """A group of people sharing expenses."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    members: Mapped[list["Member"]] = relationship(
        "Member", back_populates="group", cascade="all, delete-orphan"
    )
    expenses: Mapped[list["Expense"]] = relationship(  # type: ignore[name-defined]
        "Expense", back_populates="group", cascade="all, delete-orphan"
    )
    settlements: Mapped[list["Settlement"]] = relationship(  # type: ignore[name-defined]
        "Settlement", back_populates="group", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Group id={self.id} name={self.name!r}>"


class Member(Base):
    """A named participant within a group."""

    __tablename__ = "members"
    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_member_group_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="members")

    # Expenses where this member is the payer
    paid_expenses: Mapped[list["Expense"]] = relationship(  # type: ignore[name-defined]
        "Expense", back_populates="payer", foreign_keys="Expense.payer_id"
    )

    # Participations in expenses
    expense_participations: Mapped[list["ExpenseParticipant"]] = relationship(  # type: ignore[name-defined]
        "ExpenseParticipant", back_populates="member"
    )

    # Settlements where this member paid
    settlements_paid: Mapped[list["Settlement"]] = relationship(  # type: ignore[name-defined]
        "Settlement", back_populates="payer", foreign_keys="Settlement.payer_id"
    )

    # Settlements where this member received
    settlements_received: Mapped[list["Settlement"]] = relationship(  # type: ignore[name-defined]
        "Settlement", back_populates="receiver", foreign_keys="Settlement.receiver_id"
    )

    def __repr__(self) -> str:
        return f"<Member id={self.id} name={self.name!r} group_id={self.group_id}>"
