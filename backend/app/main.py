import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, users, audit, cas, certificates, crl, ocsp, dashboard, tokens, settings as settings_router, templates, tls
from app.mcp_server import mcp


@asynccontextmanager
async def lifespan(app_instance):
    if os.environ.get("TESTING") != "1":
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.scheduler.jobs import regenerate_crls, check_expirations, cleanup_audit_logs, get_crl_interval_minutes

        crl_minutes = get_crl_interval_minutes()
        scheduler = BackgroundScheduler()
        scheduler.add_job(regenerate_crls, "interval", minutes=crl_minutes, id="crl_regen")
        scheduler.add_job(check_expirations, "interval", hours=24, id="expiry_check")
        scheduler.add_job(cleanup_audit_logs, "interval", hours=24, id="audit_cleanup")
        scheduler.start()
        async with mcp.session_manager.run():
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
app.include_router(tokens.router)
app.include_router(settings_router.router)
app.include_router(templates.router)
app.include_router(tls.router)

app.mount("", mcp.streamable_http_app())


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/v1")
def api_info():
    return {
        "name": "Certifactory API",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


from fastapi.responses import RedirectResponse


@app.get("/api/v1/docs")
def api_docs_redirect():
    return RedirectResponse(url="/docs")


@app.get("/api/v1/redoc")
def api_redoc_redirect():
    return RedirectResponse(url="/redoc")
