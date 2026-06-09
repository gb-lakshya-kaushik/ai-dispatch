from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    service_order_id: Mapped[str] = mapped_column(ForeignKey("service_orders.id"), nullable=False)
    personnel_id: Mapped[str] = mapped_column(ForeignKey("personnel.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'lead', 'member', 'driver'
    crew_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    individual_score: Mapped[float | None] = mapped_column(Float, nullable=True)
