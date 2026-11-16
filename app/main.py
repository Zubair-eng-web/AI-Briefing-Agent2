import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.auth import router as auth_router
from app.api.routes import router
from app.api.security import require_api_key
from app.core.config import settings
from app.api.middleware import add_http_middleware
from app.core.database import init_db
from app.core.logging_setup import configure_logging
from app.core.security_checks import security_warnings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # server start hote hi tables tayyar
    for warning in security_warnings(settings):
        logging.getLogger("app.startup").warning(warning)
    yield


configure_logging(settings.log_level, settings.log_json)
app = FastAPI(title=settings.app_name, lifespan=lifespan)
add_http_middleware(app)
app.include_router(router, dependencies=[Depends(require_api_key)])
app.include_router(auth_router)  # register/login khule hain, baaki routes API key se


@app.get("/")
def root():
    return {"message": f"{settings.app_name} is running"}


@app.get("/health")
def health():
    return {"status": "ok", "debug": settings.debug}
