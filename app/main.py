from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.api.routes import router
from app.api.security import require_api_key
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # server start hote hi tables tayyar
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router, dependencies=[Depends(require_api_key)])


@app.get("/")
def root():
    return {"message": f"{settings.app_name} is running"}


@app.get("/health")
def health():
    return {"status": "ok", "debug": settings.debug}
