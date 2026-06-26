from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.service_order import ServiceOrder
from app.schemas.schemas import ServiceOrderSchema

router = APIRouter()


@router.get("/service-orders", response_model=list[ServiceOrderSchema])
def list_service_orders(db: Session = Depends(get_db)):
    orders = db.query(ServiceOrder).all()
    return [
        ServiceOrderSchema(
            id=o.id,
            customer_id=o.customer_id,
            customer_name=o.customer.name if o.customer else None,
            closure_type=o.closure_type,
            crew_size=o.crew_size,
            leads_required=o.leads_required,
            vehicle_id=o.vehicle_id,
            vehicle_name=o.vehicle.name if o.vehicle else None,
            location=o.location,
            start_time=o.start_time,
            end_time=o.end_time,
            priority=o.priority,
            notes=o.notes,
        )
        for o in orders
    ]


@router.get("/service-orders/{order_id}", response_model=ServiceOrderSchema)
def get_service_order(order_id: str, db: Session = Depends(get_db)):
    # H3 FIX: Return 404 instead of 500 on missing order
    o = db.query(ServiceOrder).filter_by(id=order_id).first()
    if o is None:
        raise HTTPException(status_code=404, detail=f"Service order '{order_id}' not found")
    return ServiceOrderSchema(
        id=o.id,
        customer_id=o.customer_id,
        customer_name=o.customer.name if o.customer else None,
        closure_type=o.closure_type,
        crew_size=o.crew_size,
        leads_required=o.leads_required,
        vehicle_id=o.vehicle_id,
        vehicle_name=o.vehicle.name if o.vehicle else None,
        location=o.location,
        start_time=o.start_time,
        end_time=o.end_time,
        priority=o.priority,
        notes=o.notes,
    )
