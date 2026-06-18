import hashlib
import socket
import ssl

import httpx
import dns.resolver

from app.services.acme_jws import jwk_thumbprint, b64url_encode

_HTTP_TIMEOUT = 10
_ACME_EXTENSION_OID = "1.3.6.1.5.5.7.1.31"


def key_authorization(token: str, jwk: dict) -> str:
    return f"{token}.{jwk_thumbprint(jwk)}"


def dns_txt_value(token: str, jwk: dict) -> str:
    ka = key_authorization(token, jwk)
    return b64url_encode(hashlib.sha256(ka.encode()).digest())


def validate_http_01(domain: str, token: str, jwk: dict) -> bool:
    expected = key_authorization(token, jwk)
    url = f"http://{domain}/.well-known/acme-challenge/{token}"
    try:
        resp = httpx.get(url, timeout=_HTTP_TIMEOUT, follow_redirects=False)
        if resp.status_code != 200:
            return False
        return resp.text.strip() == expected
    except Exception:
        return False


def validate_dns_01(domain: str, token: str, jwk: dict) -> bool:
    expected = dns_txt_value(token, jwk)
    record_name = f"_acme-challenge.{domain}"
    try:
        answers = dns.resolver.resolve(record_name, "TXT")
        for rdata in answers:
            for txt in rdata.strings:
                value = txt.decode() if isinstance(txt, bytes) else txt
                if value == expected:
                    return True
        return False
    except Exception:
        return False


def validate_tls_alpn_01(domain: str, token: str, jwk: dict) -> bool:
    ka = key_authorization(token, jwk)
    expected_digest = hashlib.sha256(ka.encode()).digest()
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_alpn_protocols(["acme-tls/1"])
        with socket.create_connection((domain, 443), timeout=_HTTP_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                der = ssock.getpeercert(binary_form=True)
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        for ext in cert.extensions:
            if ext.oid.dotted_string == _ACME_EXTENSION_OID:
                ext_bytes = ext.value.value if hasattr(ext.value, "value") else bytes(ext.value.public_bytes())
                return expected_digest in ext_bytes
        return False
    except Exception:
        return False
