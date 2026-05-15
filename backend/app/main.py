import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, users, audit, cas, certificates, crl, ocsp, dashboard


@asynccontextmanager
async def lifespan(app_instance):
    if os.environ.get("TESTING") != "1":
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.scheduler.jobs import regenerate_crls, check_expirations

        scheduler = BackgroundScheduler()
        scheduler.add_job(regenerate_crls, "interval", hours=1, id="crl_regen")
        scheduler.add_job(check_expirations, "interval", hours=24, id="expiry_check")
        scheduler.start()
        yield
        scheduler.shutdown()
    else:
        yield


app = FastAPI(title="Certifactory", version="0.1.0", lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(cas.router)
app.include_router(certificates.router)
app.include_router(crl.router)
app.include_router(ocsp.router)
app.include_router(dashboard.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
