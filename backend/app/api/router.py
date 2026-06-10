"""Main API router combining all sub-routers."""
from fastapi import APIRouter

from app.api.personnel import router as personnel_router
from app.api.service_orders import router as service_orders_router
from app.api.vehicles import router as vehicles_router
from app.api.customers import router as customers_router
from app.api.eligibility import router as eligibility_router
from app.api.scoring import router as scoring_router
from app.api.crews import router as crews_router
from app.api.optimization import router as optimization_router
from app.api.copilot import router as copilot_router
from app.api.config import router as config_router

api_router = APIRouter(prefix="/api")

api_router.include_router(personnel_router, tags=["Personnel"])
api_router.include_router(service_orders_router, tags=["Service Orders"])
api_router.include_router(vehicles_router, tags=["Vehicles"])
api_router.include_router(customers_router, tags=["Customers"])
api_router.include_router(eligibility_router, tags=["Eligibility"])
api_router.include_router(scoring_router, tags=["Scoring"])
api_router.include_router(crews_router, tags=["Crews"])
api_router.include_router(optimization_router, tags=["Optimization"])
api_router.include_router(copilot_router, tags=["Copilot"])
api_router.include_router(config_router, tags=["Config"])
