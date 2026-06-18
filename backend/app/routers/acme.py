import json

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services.acme_service import acme_service
from app.services.acme_jws import verify_jws, decode_protected, b64url_decode, jwk_thumbprint
from app.services.acme_nonce import nonce_manager
from app.services.settings_service import SettingsService
from app.models import AcmeAccount


class AcmeError(Exception):
    def __init__(self, error_type: str, detail: str, status: int):
        self.error_type = error_type
        self.detail = detail
        self.status = status

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


async def parse_jws_request(request: Request, db: Session, expect_jwk: bool):
    try:
        body = await request.json()
    except Exception:
        raise AcmeError("malformed", "Request body is not valid JSON", 400)

    protected_b64 = body.get("protected")
    payload_b64 = body.get("payload", "")
    signature_b64 = body.get("signature")
    if not protected_b64 or not signature_b64:
        raise AcmeError("malformed", "Missing JWS fields", 400)

    try:
        protected = decode_protected(protected_b64)
    except Exception:
        raise AcmeError("malformed", "Invalid protected header", 400)

    if protected.get("url") != str(request.url):
        raise AcmeError("unauthorized", "JWS url does not match request URL", 401)

    nonce = protected.get("nonce")
    if not nonce or not nonce_manager.consume(nonce):
        raise AcmeError("badNonce", "Invalid or missing nonce", 400)

    if expect_jwk:
        jwk = protected.get("jwk")
        if not jwk:
            raise AcmeError("malformed", "Expected jwk in protected header", 400)
    else:
        kid = protected.get("kid")
        if not kid:
            raise AcmeError("malformed", "Expected kid in protected header", 400)
        account_id = kid.rstrip("/").split("/")[-1]
        account = db.query(AcmeAccount).filter(AcmeAccount.id == account_id).first()
        if not account:
            raise AcmeError("accountDoesNotExist", "Unknown account", 400)
        jwk = account.jwk

    if not verify_jws(protected, payload_b64, signature_b64, jwk, protected_b64=protected_b64):
        raise AcmeError("unauthorized", "JWS signature verification failed", 401)

    if payload_b64 == "":
        payload = {}
    else:
        try:
            payload = json.loads(b64url_decode(payload_b64))
        except Exception:
            raise AcmeError("malformed", "Invalid payload", 400)

    return protected, payload, jwk


def _error_response(e: AcmeError) -> JSONResponse:
    return _acme_error(e.error_type, e.detail, e.status)


def _order_json(request: Request, order, authzs) -> dict:
    base = _base_url(request)
    body = {
        "status": order.status,
        "expires": order.expires.isoformat() + "Z",
        "identifiers": order.identifiers,
        "authorizations": [f"{base}/acme/authz/{a.id}" for a in authzs],
        "finalize": f"{base}/acme/order/{order.id}/finalize",
    }
    if order.certificate_id:
        body["certificate"] = f"{base}/acme/order/{order.id}/cert"
    return body


def _authz_json(request: Request, authz) -> dict:
    base = _base_url(request)
    challenges = []
    for ch in authz.challenges:
        challenges.append({
            "type": ch["type"],
            "url": f"{base}/acme/challenge/{authz.id}/{ch['type']}",
            "token": ch["token"],
            "status": ch["status"],
        })
    return {
        "status": authz.status,
        "expires": authz.expires.isoformat() + "Z",
        "identifier": {"type": authz.identifier_type, "value": authz.identifier_value},
        "challenges": challenges,
    }


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


@router.post("/new-account")
async def new_account(request: Request, db: Session = Depends(get_db)):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=True)
    except AcmeError as e:
        return _error_response(e)

    only_existing = payload.get("onlyReturnExisting", False)
    try:
        if not settings_service.get(db, "acme_registration_open") and not only_existing:
            existing = acme_service.get_account_by_thumbprint(db, jwk_thumbprint(jwk))
            if not existing:
                return _acme_error("unauthorized", "Registration is closed", 403)
        account = acme_service.get_or_create_account(db, jwk, payload.get("contact"), only_existing)
    except ValueError as e:
        return _acme_error(str(e), "Account does not exist", 400)

    base = _base_url(request)
    resp = JSONResponse(
        status_code=201,
        content={"status": account.status, "contact": account.contact or [], "orders": f"{base}/acme/account/{account.id}/orders"},
    )
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Location"] = f"{base}/acme/account/{account.id}"
    return resp


@router.post("/new-order")
@router.post("/{ca_id}/new-order")
async def new_order(request: Request, db: Session = Depends(get_db), ca_id: str | None = None):
    if not _require_enabled(db):
        return _acme_error("unauthorized", "ACME server is disabled", 403)
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)

    resolved_ca = _resolve_ca_id(db, ca_id)
    if not resolved_ca:
        return _acme_error("unauthorized", "No CA configured for ACME", 403)

    identifiers = payload.get("identifiers", [])
    if not identifiers:
        return _acme_error("malformed", "No identifiers in order", 400)

    allowed = settings_service.get(db, "acme_allowed_domains")
    for ident in identifiers:
        if not acme_service.domain_allowed(allowed, ident["value"]):
            return _acme_error("rejectedIdentifier", f"Domain not allowed: {ident['value']}", 403)

    kid = protected["kid"]
    account_id = kid.rstrip("/").split("/")[-1]
    order = acme_service.create_order(db, account_id, resolved_ca, identifiers, None, None)
    authzs = acme_service.list_authorizations(db, order.id)
    base = _base_url(request)
    resp = JSONResponse(status_code=201, content=_order_json(request, order, authzs))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    resp.headers["Location"] = f"{base}/acme/order/{order.id}"
    return resp


@router.post("/order/{order_id}")
async def get_order_endpoint(order_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    order = acme_service.get_order(db, order_id)
    if not order:
        return _acme_error("malformed", "Order not found", 404)
    authzs = acme_service.list_authorizations(db, order.id)
    resp = JSONResponse(content=_order_json(request, order, authzs))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.post("/authz/{authz_id}")
async def get_authz_endpoint(authz_id: str, request: Request, db: Session = Depends(get_db)):
    try:
        await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    authz = acme_service.get_authorization(db, authz_id)
    if not authz:
        return _acme_error("malformed", "Authorization not found", 404)
    resp = JSONResponse(content=_authz_json(request, authz))
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp


@router.post("/challenge/{authz_id}/{challenge_type}")
async def respond_challenge(authz_id: str, challenge_type: str, request: Request, db: Session = Depends(get_db)):
    try:
        protected, payload, jwk = await parse_jws_request(request, db, expect_jwk=False)
    except AcmeError as e:
        return _error_response(e)
    try:
        authz = acme_service.process_challenge(db, authz_id, challenge_type, jwk)
    except ValueError as e:
        return _acme_error(str(e), "Challenge processing failed", 400)
    base = _base_url(request)
    matching = next((c for c in authz.challenges if c["type"] == challenge_type), None)
    resp = JSONResponse(content={
        "type": challenge_type,
        "url": f"{base}/acme/challenge/{authz.id}/{challenge_type}",
        "token": matching["token"],
        "status": matching["status"],
    })
    resp.headers["Replay-Nonce"] = nonce_manager.issue()
    return resp
