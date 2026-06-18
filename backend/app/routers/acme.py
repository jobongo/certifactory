from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.acme_service import acme_service
from app.services.acme_nonce import nonce_manager
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/acme", tags=["acme"])
settings_service = SettingsService()

_PROBLEM = "application/problem+json"
_ERROR_PREFIX = "urn:ietf:params:acme:error:"


def _acme_error(error_type: str, detail: str, status: int) -> JSONResponse:
    resp = JSONResponse(
        status_code=status,
        content={"type": f"{_ERROR_PREFIX}{error_type}", "detail": detail, "status": status},
        media_type=_PROBLEM,
    )
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


def _require_enabled(db: Session):
    if not settings_service.get(db, "acme_enabled"):
        return False
    return True


def _resolve_ca_id(db: Session, ca_id: str | None) -> str | None:
    if ca_id:
        return ca_id
    default = settings_service.get(db, "acme_default_ca_id")
    return default or None


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _directory_body(request: Request, prefix: str) -> dict:
    base = _base_url(request)
    return {
        "newNonce": f"{base}{prefix}/new-nonce",
        "newAccount": f"{base}{prefix}/new-account",
        "newOrder": f"{base}{prefix}/new-order",
        "revokeCert": f"{base}{prefix}/revoke-cert",
        "keyChange": f"{base}{prefix}/key-change",
    }


@router.get("/directory")
def directory(request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    resp = JSONResponse(content=_directory_body(request, "/acme"))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.get("/{ca_id}/directory")
def directory_for_ca(ca_id: str, request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    resp = JSONResponse(content=_directory_body(request, f"/acme/{ca_id}"))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.api_route("/new-nonce", methods=["GET", "HEAD"])
def new_nonce(db: Session = Depends(get_db)):
    resp = Response(status_code=200)
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Cache-Control"] = "no-store"
    return resp
