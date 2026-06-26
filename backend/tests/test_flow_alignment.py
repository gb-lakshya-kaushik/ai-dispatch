import pytest
from app.engines.rules import (
    driver_class_meets_requirement,
    vehicle_driver_meets_requirement,
)
from app.models import Personnel, Skill, Certification, PersonnelSkill, PersonnelCertification
from app.database import Base, engine, SessionLocal
from data.seed import _seed_dynamic_rules

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    _seed_dynamic_rules(db)
    db.commit()
    yield db

def test_closure_type_skills(setup_db):
    db = setup_db
    from app.models.rules import ClosureSkillRule
    freeway_rule = db.query(ClosureSkillRule).filter_by(closure_type="freeway_closure").first()
    high_speed_rule = db.query(ClosureSkillRule).filter_by(closure_type="high_speed_single_lane").first()
    flagging_rule = db.query(ClosureSkillRule).filter_by(closure_type="flagging").first()

    assert freeway_rule.lead_skill == "TMA Operator Skill"
    assert high_speed_rule.lead_skill == "Installer High Speed Single Lane Closure"
    assert freeway_rule.member_skill == "General Assistant"
    assert high_speed_rule.member_skill == "General Assistant"
    assert flagging_rule.member_skill == "General Assistant"

def test_driver_class_meets_requirement():
    assert driver_class_meets_requirement("DT", "DT") is True
    assert driver_class_meets_requirement("D4", "DT") is True
    assert driver_class_meets_requirement("D1", "D2") is False
    assert driver_class_meets_requirement("D1", "D1+ & LT") is True  # Base class D1 matches
    assert driver_class_meets_requirement("DT", "D1+ & LT") is False

def test_vehicle_driver_meets_requirement():
    # Service Truck + Light Tower (D1+ & LT)
    assert vehicle_driver_meets_requirement("D1", ["Light Tower Certification"], "Service Truck + Light Tower", "D1+ & LT", "CA", False) is True
    assert vehicle_driver_meets_requirement("D1", [], "Service Truck + Light Tower", "D1+ & LT", "CA", False) is False
    
    # AFAD (D1+ & AFAD Cert)
    assert vehicle_driver_meets_requirement("D2", ["AFAD Certification"], "AFAD", "D1+ & AFAD Cert", "CA", False) is True
    assert vehicle_driver_meets_requirement("D2", [], "AFAD", "D1+ & AFAD Cert", "CA", False) is False

    # Stakebed (D2+, CA/WA vs MI vs TX)
    # CA/WA doesn't need DOT Med Card or Chauffeur
    assert vehicle_driver_meets_requirement("D2", [], "Stakebed", "D2", "CA", False) is True
    # TX needs DOT Med Card
    assert vehicle_driver_meets_requirement("D2", [], "Stakebed", "D2", "TX", False) is False
    assert vehicle_driver_meets_requirement("D2", ["DOT Medical Card"], "Stakebed", "D2", "TX", False) is True
    # MI needs Chauffeur License (and DOT Med Card since it's not CA/WA)
    assert vehicle_driver_meets_requirement("D2", ["DOT Medical Card", "Chauffeur License"], "Stakebed", "D2", "MI", False) is True
    assert vehicle_driver_meets_requirement("D2", ["DOT Medical Card"], "Stakebed", "D2", "MI", False) is False

    # TMA Contingency
    # TMA Non-Freeway, driver is D3, required is D3 -> normal match
    assert vehicle_driver_meets_requirement("D3", [], "TMA Non-Freeway", "D3", "CA", False) is True
    # Suppose TMA requires D3, but driver is DT, vehicle is TMA -> Contingency might say D3 or D4 can be used if non-freeway. 
    # Wait, the rule is: if TMA needed on non-freeway, D3 or D4 CAN be used. 
    # That means if required is D3, D3/D4 meets it naturally by hierarchy. 
    # The contingency rule in the code: if `has_class` in ("D3", "D4") and not is_freeway, return True.
    assert vehicle_driver_meets_requirement("D3", [], "TMA", "D4", "CA", False) is True  # Override contingency
    assert vehicle_driver_meets_requirement("D2", [], "TMA", "D4", "CA", False) is False
