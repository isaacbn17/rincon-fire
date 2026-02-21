from fastapi import APIRouter

from app.api.routes.areas import router as areas_router
from app.api.routes.fire_areas import router as fire_areas_router
from app.api.routes.health import router as health_router
from app.api.routes.location import router as location_router
from app.api.routes.models import router as models_router
from app.api.routes.satellite import router as satellite_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(models_router)
api_router.include_router(fire_areas_router)
api_router.include_router(areas_router)
api_router.include_router(location_router)
api_router.include_router(satellite_router)
