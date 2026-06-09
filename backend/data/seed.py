"""Seed script — 300 personnel, 60 service orders, 10 customers, 10 vehicles."""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models import (
    Personnel, Skill, Certification, PersonnelSkill, PersonnelCertification,
    Customer, CustomerPreference, Vehicle, ServiceOrder, ScoringWeight, JobHistory,
)

RNG = random.Random(42)

FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
    "Thomas", "Christopher", "Charles", "Daniel", "Matthew", "Anthony", "Mark",
    "Donald", "Steven", "Andrew", "Paul", "Joshua", "Kenneth", "Kevin", "Brian",
    "George", "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan",
    "Jacob", "Gary", "Nicholas", "Eric", "Jonathan", "Stephen", "Larry", "Justin",
    "Scott", "Brandon", "Benjamin", "Samuel", "Raymond", "Gregory", "Frank", "Alexander",
    "Patrick", "Jack", "Dennis", "Jerry", "Tyler", "Aaron", "Jose", "Adam",
    "Nathan", "Henry", "Douglas", "Peter", "Zachary", "Kyle",
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica",
    "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra", "Ashley",
    "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol", "Amanda", "Melissa",
    "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura", "Cynthia", "Kathleen", "Amy",
    "Angela", "Shirley", "Anna", "Brenda", "Pamela", "Emma", "Nicole", "Helen",
    "Samantha", "Katherine", "Christine", "Debra", "Rachel", "Carolyn", "Janet", "Catherine",
    "Maria", "Heather", "Diane", "Ruth", "Julie", "Olivia", "Joyce", "Virginia",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner",
    "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper",
    "Peterson", "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox",
]

LEAD_SKILLS = [
    "Installer Flagging Operation",
    "Installer Single Lane",
    "Installer Multi Lane Closure",
    "Installer Road Closure",
    "Installer Shoulder Closure",
    "Installer Lane Shift",
]

CLOSURE_TYPES = ["flagging", "single_lane", "multi_lane", "road_closure", "shoulder_closure", "lane_shift"]

DRIVER_CLASSES = [None, "DT", "D1", "D2", "D3", "D4"]
DRIVER_WEIGHTS = [20, 25, 20, 15, 12, 8]


def seed_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _seed_skills(db)
        _seed_certifications(db)
        _seed_personnel(db)
        _seed_customers(db)
        _seed_vehicles(db)
        _seed_service_orders(db)
        _seed_scoring_weights(db)
        _seed_job_history(db)
        db.commit()
        print("Database seeded: 300 personnel, 60 orders, 10 customers, 10 vehicles.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


def _seed_skills(db: Session):
    skills = LEAD_SKILLS + ["General Assistant"]
    for name in skills:
        db.add(Skill(name=name))
    db.flush()


def _seed_certifications(db: Session):
    certs = [
        "Local Flagger Certification",
        "AFAD Certification",
        "DOT Medical Card",
        "Chauffeur License",
        "Light Tower Certification",
    ]
    for name in certs:
        db.add(Certification(name=name))
    db.flush()


def _seed_personnel(db: Session):
    flagger_cert = db.query(Certification).filter_by(name="Local Flagger Certification").one()
    extra_certs = db.query(Certification).filter(Certification.name != "Local Flagger Certification").all()
    skill_map = {s.name: s for s in db.query(Skill).all()}

    names_pool = []
    for fn in FIRST_NAMES:
        for ln in LAST_NAMES:
            names_pool.append(f"{fn} {ln}")
    RNG.shuffle(names_pool)

    for i in range(300):
        tc_id = f"TC{i+1:03d}"
        name = names_pool[i]
        is_journeyman = i < 180
        tc_type = "journeyman" if is_journeyman else "apprentice"
        rate = round(RNG.uniform(35, 55), 2) if is_journeyman else round(RNG.uniform(22, 34), 2)
        hours = RNG.randint(400, 2000)
        driver_class = RNG.choices(DRIVER_CLASSES, weights=DRIVER_WEIGHTS, k=1)[0]

        p = Personnel(
            id=tc_id, name=name, type=tc_type,
            hourly_rate=rate, hours_worked_ytd=hours,
            is_available=True, driver_class=driver_class,
        )
        db.add(p)
        db.flush()

        db.add(PersonnelCertification(personnel_id=tc_id, certification_id=flagger_cert.id))
        if RNG.random() < 0.3:
            cert = RNG.choice(extra_certs)
            db.add(PersonnelCertification(personnel_id=tc_id, certification_id=cert.id))

        if is_journeyman:
            num_lead_skills = RNG.choices([1, 2, 3], weights=[50, 35, 15], k=1)[0]
            chosen_skills = RNG.sample(LEAD_SKILLS, num_lead_skills)
            for skill_name in chosen_skills:
                db.add(PersonnelSkill(personnel_id=tc_id, skill_id=skill_map[skill_name].id))
            db.add(PersonnelSkill(personnel_id=tc_id, skill_id=skill_map["General Assistant"].id))
        else:
            db.add(PersonnelSkill(personnel_id=tc_id, skill_id=skill_map["General Assistant"].id))

    db.flush()
    print(f"  -> 300 personnel created (180 journeymen, 120 apprentices)")


def _seed_customers(db: Session):
    customer_names = [
        ("CUST001", "Alpha Highway Corp", "Major highway contractor, prefers experienced crews"),
        ("CUST002", "Metro City DOT", "Municipal projects, strict timelines"),
        ("CUST003", "Pacific Construction", "Large-scale multi-lane projects"),
        ("CUST004", "SafeRoads Inc", "Safety-focused, cost-conscious"),
        ("CUST005", "Urban Transit Authority", "Public transit corridor work"),
        ("CUST006", "Valley Infrastructure", "Rural and suburban road maintenance"),
        ("CUST007", "Coastal Development", "Bridge and coastal road projects"),
        ("CUST008", "Summit Engineering", "Mountain pass and steep grade work"),
        ("CUST009", "Prairie Roads LLC", "Flat terrain highway extensions"),
        ("CUST010", "River Bridge Authority", "Bridge approach and overpass work"),
    ]
    for cid, name, notes in customer_names:
        db.add(Customer(id=cid, name=name, notes=notes))
    db.flush()

    all_tc_ids = [f"TC{i+1:03d}" for i in range(300)]
    for cid, _, _ in customer_names:
        num_prefs = RNG.randint(3, 8)
        preferred = RNG.sample(all_tc_ids, num_prefs)
        for pid in preferred:
            level = RNG.choice([1, 2, 3])
            db.add(CustomerPreference(customer_id=cid, personnel_id=pid, preference_level=level))

    db.flush()
    print(f"  -> 10 customers with preferences created")


def _seed_vehicles(db: Session):
    vehicles = [
        ("VEH001", "Service Truck Alpha", "Service Truck", "DT"),
        ("VEH002", "Service Truck Bravo", "Service Truck", "DT"),
        ("VEH003", "Service Truck Charlie", "Service Truck", "DT"),
        ("VEH004", "FAS Unit 1", "Service Truck + FAS", "D1"),
        ("VEH005", "FAS Unit 2", "Service Truck + FAS", "D1"),
        ("VEH006", "FAS Unit 3", "Service Truck + FAS", "D1"),
        ("VEH007", "Stakebed Alpha", "Stakebed", "D2"),
        ("VEH008", "Stakebed Bravo", "Stakebed", "D2"),
        ("VEH009", "TMA Non-Freeway", "TMA Non-Freeway", "D3"),
        ("VEH010", "TMA Freeway", "TMA Freeway", "D4"),
    ]
    for vid, name, vtype, req_class in vehicles:
        db.add(Vehicle(id=vid, name=name, type=vtype, required_driver_class=req_class))
    db.flush()
    print(f"  -> 10 vehicles created")


def _seed_service_orders(db: Session):
    vehicle_ids = [f"VEH{i+1:03d}" for i in range(10)]
    customer_ids = [f"CUST{i+1:03d}" for i in range(10)]

    locations = [
        "Highway 101 MM 45", "Interstate 5 NB", "Route 66 Junction", "Main St Downtown",
        "Oak Ave Intersection", "Industrial Park Rd", "School Zone Cedar Blvd",
        "Bridge Approach Rd", "Freeway On-Ramp 12A", "Festival Grounds Perimeter",
        "Highway 99 Overpass", "Airport Blvd Extension", "Harbor Freeway Connector",
        "Mountain Pass Rd", "Valley View Intersection", "Coastal Highway 1",
        "University Dr Corridor", "Mall Ring Road", "Hospital Access Rd",
        "Train Station Approach", "Park Ave Lane 3", "Canyon Rd Shoulder",
        "Township Line Rd", "Expressway Exit 42", "County Line Bridge",
        "Lakeside Dr", "Forest Service Rd 7", "Stadium Access Ramp",
        "Warehouse District", "Riverfront Blvd",
    ]

    # Time slots for feasibility (spread 60 orders across non-competing windows)
    slots = [
        # (start_hour, end_hour, count)
        (5, 10, 12),   # Slot A: early morning
        (6, 11, 12),   # Slot B: morning (overlaps with A)
        (11, 15, 10),  # Slot C: midday
        (13, 18, 12),  # Slot D: afternoon (overlaps with C slightly)
        (14, 19, 10),  # Slot E: late afternoon (overlaps with D)
        (9, 15, 4),    # Slot F: bridge orders
    ]

    crew_size_choices = [2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 5, 5, 6]

    order_idx = 0
    for slot_start, slot_end, count in slots:
        for _ in range(count):
            order_idx += 1
            oid = f"SO{order_idx:03d}"
            closure = RNG.choice(CLOSURE_TYPES)
            crew_size = RNG.choice(crew_size_choices)
            cust = RNG.choice(customer_ids)
            has_vehicle = RNG.random() < 0.7
            veh = RNG.choice(vehicle_ids) if has_vehicle else None
            loc = RNG.choice(locations)
            priority = RNG.randint(1, 10)

            start_time = f"2026-06-10T{slot_start:02d}:00:00"
            end_time = f"2026-06-10T{slot_end:02d}:00:00"

            db.add(ServiceOrder(
                id=oid, customer_id=cust, closure_type=closure,
                crew_size=crew_size, leads_required=1, vehicle_id=veh,
                location=loc, start_time=start_time, end_time=end_time,
                priority=priority, notes=None,
            ))

    db.flush()
    print(f"  -> 60 service orders created across 6 time slots")


def _seed_scoring_weights(db: Session):
    weights = [
        ("customer_preference", 20.0, "Bonus for customer-preferred employees"),
        ("similar_job_experience", 15.0, "Worked similar closure type before"),
        ("hour_balancing", 25.0, "Favor employees with fewer hours YTD"),
        ("cost_efficiency", 10.0, "Favor lower hourly rates"),
        ("skill_match", 30.0, "Exact skill match vs general eligibility"),
    ]
    for factor, weight, desc in weights:
        db.add(ScoringWeight(factor=factor, weight=weight, description=desc))
    db.flush()


def _seed_job_history(db: Session):
    all_tc_ids = [f"TC{i+1:03d}" for i in range(300)]
    customer_ids = [f"CUST{i+1:03d}" for i in range(10)]

    months = ["01", "02", "03", "04", "05"]
    days = [f"{d:02d}" for d in range(1, 29)]

    for _ in range(500):
        pid = RNG.choice(all_tc_ids)
        closure = RNG.choice(CLOSURE_TYPES)
        cust = RNG.choice(customer_ids)
        month = RNG.choice(months)
        day = RNG.choice(days)
        date = f"2026-{month}-{day}"
        rating = round(RNG.uniform(3.5, 5.0), 1)
        db.add(JobHistory(
            personnel_id=pid, closure_type=closure,
            customer_id=cust, completed_date=date,
            performance_rating=rating,
        ))

    db.flush()
    print(f"  -> 500 job history entries created")


if __name__ == "__main__":
    seed_database()
