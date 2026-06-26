from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PersonnelSkill(Base):
    __tablename__ = "personnel_skills"

    personnel_id: Mapped[str] = mapped_column(ForeignKey("personnel.id"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)


class PersonnelCertification(Base):
    __tablename__ = "personnel_certifications"

    personnel_id: Mapped[str] = mapped_column(ForeignKey("personnel.id"), primary_key=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), primary_key=True)
    expiry_date: Mapped[str | None] = mapped_column(String, nullable=True)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Personnel(Base):
    __tablename__ = "personnel"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'TC' or 'apprentice'
    hourly_rate: Mapped[float] = mapped_column(Float, default=20.0)
    hours_worked_ytd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="Active")
    driver_class: Mapped[str | None] = mapped_column(String, nullable=True)  # DT, D1, D2, D3, D4
    seniority: Mapped[int] = mapped_column(Integer, default=1)  # 1-5 scale (e.g., TC5)

    skills: Mapped[list["Skill"]] = relationship(
        "Skill", secondary="personnel_skills", lazy="joined"
    )
    certifications: Mapped[list["Certification"]] = relationship(
        "Certification", secondary="personnel_certifications", lazy="joined"
    )
