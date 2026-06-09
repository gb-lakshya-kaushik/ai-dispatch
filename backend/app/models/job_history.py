from sqlalchemy import String, Float, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobHistory(Base):
    __tablename__ = "job_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    personnel_id: Mapped[str] = mapped_column(ForeignKey("personnel.id"), nullable=False)
    closure_type: Mapped[str] = mapped_column(String, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    completed_date: Mapped[str] = mapped_column(String, nullable=False)
    performance_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
