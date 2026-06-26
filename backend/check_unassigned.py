import sys
sys.path.insert(0, './backend')
from app.database import SessionLocal
from app.models.service_order import ServiceOrder
from app.services.dispatch import DispatchService
from collections import Counter

db = SessionLocal()
dates = [o.start_time[:10] for o in db.query(ServiceOrder).all()]
most_common_date = Counter(dates).most_common(1)[0][0] if dates else None

res = DispatchService(db).run_full_pipeline(most_common_date)
unassigned = res.optimization.unassigned_orders

print("Unassigned count:", len(unassigned))
for oid in unassigned:
    elig_leads = len(res.eligibility[oid].eligible_leads) if oid in res.eligibility else 0
    elig_members = len(res.eligibility[oid].eligible_members) if oid in res.eligibility else 0
    crews_built = len(res.crews.get(oid, []))
    print(f"{oid}: Elig_leads={elig_leads}, Elig_members={elig_members}, Crews_built={crews_built}")
