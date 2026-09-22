"""
Settlement SQLAlchemy model.

Settlement: Records when one member pays another to settle a debt.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Settlement(Base):
    """A payment from one member to another to settle a debt."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # The member who PAID (the debtor settling their debt)
    payer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False
    )
    # The member who RECEIVED the payment (the creditor)
    receiver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("members.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="settlements")  # type: ignore[name-defined]
    payer: Mapped["Member"] = relationship(  # type: ignore[name-defined]
        "Member", back_populates="settlements_paid", foreign_keys=[payer_id]
    )
    receiver: Mapped["Member"] = relationship(  # type: ignore[name-defined]
        "Member", back_populates="settlements_received", foreign_keys=[receiver_id]
    )

    def __repr__(self) -> str:
        return (
            f"<Settlement id={self.id} "
            f"payer_id={self.payer_id} "
            f"receiver_id={self.receiver_id} "
            f"amount={self.amount}>"
        )
