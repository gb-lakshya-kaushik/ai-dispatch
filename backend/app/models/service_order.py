from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    closure_type: Mapped[str] = mapped_column(String, nullable=False)
    crew_size: Mapped[int] = mapped_column(Integer, nullable=False)
    leads_required: Mapped[int] = mapped_column(Integer, default=1)
    vehicle_id: Mapped[str | None] = mapped_column(ForeignKey("vehicles.id"), nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str] = mapped_column(String, nullable=False)
    end_time: Mapped[str] = mapped_column(String, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    is_prevailing_wage: Mapped[bool] = mapped_column(Boolean, default=False)
    is_journeyman_scale: Mapped[bool] = mapped_column(Boolean, default=False)
    rollover_from_id: Mapped[str | None] = mapped_column(String, nullable=True)
    operating_state: Mapped[str] = mapped_column(String, default="CA")

    customer: Mapped["Customer"] = relationship("Customer", lazy="joined")
    vehicle: Mapped["Vehicle | None"] = relationship("Vehicle", lazy="joined")


from app.models.customer import Customer
from app.models.vehicle import Vehicle
