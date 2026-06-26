from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClosureSkillRule(Base):
    __tablename__ = "closure_skill_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    closure_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    lead_skill: Mapped[str] = mapped_column(String, nullable=False)
    member_skill: Mapped[str] = mapped_column(String, nullable=False)


class VehicleDriverRule(Base):
    __tablename__ = "vehicle_driver_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_type: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    required_driver_class: Mapped[str] = mapped_column(String, nullable=False)
