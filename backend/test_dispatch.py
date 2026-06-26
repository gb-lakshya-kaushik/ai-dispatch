from app.services.dispatch import DispatchService
from app.database import SessionLocal
from app.models.service_order import ServiceOrder
import sys
db = SessionLocal()
service = DispatchService(db)
res = service.run_full_pipeline()
print("TOTAL ORDERS:", len(res.eligibility))
assigned = len(res.optimization.assignments) if res.optimization else 0
print("ASSIGNED:", assigned)
unassigned = len(res.optimization.unassigned_orders) if res.optimization else 0
print("UNASSIGNED:", unassigned)

for oid in res.optimization.unassigned_orders:
    elig = res.eligibility.get(oid)
    crews = res.crews.get(oid, [])
    order = db.query(ServiceOrder).get(oid)
    
    print(f"{oid}: Required leads: {order.leads_required}, Required Size: {order.crew_size}. Eligible Leads: {len(elig.eligible_leads)}, Eligible Members: {len(elig.eligible_members)}, Eligible Drivers: {len(elig.eligible_drivers)}. Crews: {len(crews)}")
