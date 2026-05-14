from sqlalchemy.orm import Session

from app.config import settings
from app.models import Certificate, CertificateAuthority, CertificateStatus, OCSPSigningMode
from app.services.crypto_service import CryptoService
from app.services.encryption import decrypt_private_key

crypto = CryptoService()


class OCSPService:
    def handle_request(self, db: Session, ca_id: str, request_bytes: bytes) -> bytes:
        from cryptography.x509 import ocsp
        from cryptography.hazmat.primitives import serialization

        ca = db.query(CertificateAuthority).filter(CertificateAuthority.id == ca_id).first()
        if not ca:
            return ocsp.OCSPResponseBuilder.build_unsuccessful(
                ocsp.OCSPResponseStatus.UNAUTHORIZED
            ).public_bytes(serialization.Encoding.DER)

        ocsp_req = ocsp.load_der_ocsp_request(request_bytes)
        serial_hex = format(ocsp_req.serial_number, "x")

        cert_record = db.query(Certificate).filter(
            Certificate.ca_id == ca_id,
            Certificate.serial_number == serial_hex,
        ).first()

        if not cert_record or not cert_record.certificate_pem:
            cert_status = "unknown"
        elif cert_record.status == CertificateStatus.revoked:
            cert_status = "revoked"
        else:
            cert_status = "good"

        if ca.ocsp_signing_mode == OCSPSigningMode.dedicated_cert and ca.ocsp_signing_key_encrypted:
            signing_key = decrypt_private_key(ca.ocsp_signing_key_encrypted, settings.PKI_MASTER_KEY)
            signing_cert = ca.ocsp_signing_cert_pem
        else:
            signing_key = decrypt_private_key(ca.private_key_encrypted, settings.PKI_MASTER_KEY)
            signing_cert = None

        if cert_status == "unknown":
            return ocsp.OCSPResponseBuilder.build_unsuccessful(
                ocsp.OCSPResponseStatus.UNAUTHORIZED
            ).public_bytes(serialization.Encoding.DER)

        return crypto.build_ocsp_response(
            ca.certificate_pem, signing_key, signing_cert, cert_record.certificate_pem,
            cert_status, revocation_time=cert_record.revocation_date if cert_status == "revoked" else None,
        )
