import pytest
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models import Personnel, ServiceOrder, Vehicle, Skill, PersonnelSkill, Certification, PersonnelCertification
from app.services.dispatch import DispatchService
from data.seed import _seed_dynamic_rules

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    _seed_dynamic_rules(db)
    db.commit()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)

def test_optimizer_ignores_seniority(setup_db: Session):
    db = setup_db
    # Create two TCs: one TC1, one TC5
    tc1 = Personnel(id="QA-TC1", name="Junior", type="TC", hourly_rate=20, hours_worked_ytd=100, status="Active", seniority=1)
    tc5 = Personnel(id="QA-TC5", name="Senior", type="TC", hourly_rate=30, hours_worked_ytd=100, status="Active", seniority=5)
    
    # Retrieve existing skills & certs
    flagging_skill = db.query(Skill).filter_by(name="Installer Flagging Operation").first()
    gen_skill = db.query(Skill).filter_by(name="General Assistant").first()
    local_cert = db.query(Certification).filter_by(name="Local Flagger Certification").first()
    
    if not flagging_skill:
        flagging_skill = Skill(name="Installer Flagging Operation")
        db.add(flagging_skill)
    if not gen_skill:
        gen_skill = Skill(name="General Assistant")
        db.add(gen_skill)
    if not local_cert:
        local_cert = Certification(name="Local Flagger Certification")
        db.add(local_cert)
        
    db.add_all([tc1, tc5])
    db.commit()

    db.add(PersonnelSkill(personnel_id="QA-TC1", skill_id=flagging_skill.id))
    db.add(PersonnelSkill(personnel_id="QA-TC1", skill_id=gen_skill.id))
    db.add(PersonnelCertification(personnel_id="QA-TC1", certification_id=local_cert.id))
    db.add(PersonnelSkill(personnel_id="QA-TC5", skill_id=flagging_skill.id))
    db.add(PersonnelSkill(personnel_id="QA-TC5", skill_id=gen_skill.id))
    db.add(PersonnelCertification(personnel_id="QA-TC5", certification_id=local_cert.id))
    
    order = ServiceOrder(
        id="QA-SO-TEST", customer_id="CUST1", closure_type="flagging",
        crew_size=2, start_time="2026-06-10T08:00:00", end_time="2026-06-10T12:00:00"
    )
    db.add(order)
    db.commit()

    # We want to see if the optimizer might pick TC1 as Lead and TC5 as member.
    # We will artificially make TC1 a better lead by adjusting customer preference or history?
    # Actually, if we just run the pipeline, they might be assigned randomly.
    # To force it, let's artificially change scores or let's just observe.
    
    from app.config import settings
    settings.min_crew_score_threshold = 0.0

    dispatch = DispatchService(db)
    # C1 FIX: Test orders are seeded for 2026-06-10, pass that date explicitly
    result = dispatch.run_full_pipeline(dispatch_date="2026-06-10")
    
    print(f"DEBUG Rejections: {result.eligibility['QA-SO-TEST'].rejections}")
    crews = result.crews.get("QA-SO-TEST", [])
    print(f"DEBUG Crews generated for QA-SO-TEST: {len(crews)}")
    for i, c in enumerate(crews):
        print(f"Crew {i}: Leads={[l.personnel.id for l in c.leads]}, Members={[m.personnel.id for m in c.members]}")
        
    print(f"DEBUG optimizer status: {result.optimization.status}")
    print(f"DEBUG unassigned orders: {result.optimization.unassigned_orders}")

    assignments = result.optimization.assignments.get("QA-SO-TEST", [])
    assert assignments, "No assignments made for QA-SO-TEST"
    
    lead_id = next(a.personnel_id for a in assignments if a.role == "lead")
    member_id = next(a.personnel_id for a in assignments if a.role == "member")
    
    print(f"Assigned Lead: {lead_id}, Assigned Member: {member_id}")
    
    # QA Assertion: The new Optimizer must select QA-TC5 as the Lead!
    assert lead_id == "QA-TC5", f"Expected QA-TC5 to be lead because of higher seniority, got {lead_id}"
