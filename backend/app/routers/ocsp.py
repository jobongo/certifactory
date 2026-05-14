from fastapi import APIRouter, Request, Response
from sqlalchemy.orm import Session
from fastapi import Depends

from app.dependencies import get_db
from app.services.ocsp_service import OCSPService

router = APIRouter(prefix="/api/v1/ocsp", tags=["ocsp"])
ocsp_service = OCSPService()


@router.post("/{ca_id}")
async def ocsp_responder_post(ca_id: str, request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    response_bytes = ocsp_service.handle_request(db, ca_id, body)
    return Response(content=response_bytes, media_type="application/ocsp-response")


@router.get("/{ca_id}/{encoded_request}")
def ocsp_responder_get(ca_id: str, encoded_request: str, db: Session = Depends(get_db)):
    import base64
    request_bytes = base64.b64decode(encoded_request)
    response_bytes = ocsp_service.handle_request(db, ca_id, request_bytes)
    return Response(content=response_bytes, media_type="application/ocsp-response")
