from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CustomerPreference(Base):
    __tablename__ = "customer_preferences"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), primary_key=True)
    personnel_id: Mapped[str] = mapped_column(ForeignKey("personnel.id"), primary_key=True)
    preference_level: Mapped[int] = mapped_column(Integer, default=1)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    preferred_personnel: Mapped[list["CustomerPreference"]] = relationship(
        "CustomerPreference", lazy="joined"
    )
