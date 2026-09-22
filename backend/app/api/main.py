from fastapi import APIRouter

from app.api.routes import (
    catalog,
    evidence,
    features,
    files,
    items,
    login,
    measurement_imports,
    part_setup,
    parts,
    private,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(features.router)
api_router.include_router(part_setup.router)
api_router.include_router(parts.router)
api_router.include_router(catalog.router)
api_router.include_router(evidence.router)
api_router.include_router(measurement_imports.router)
api_router.include_router(files.router)


if settings.ENABLE_TEST_ROUTES:
    api_router.include_router(private.router)
