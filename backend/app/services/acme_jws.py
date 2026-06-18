import base64
import hashlib
import json

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, ec, utils
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicNumbers, SECP256R1, SECP384R1, SECP521R1
from cryptography.exceptions import InvalidSignature


def b64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def decode_protected(protected_b64: str) -> dict:
    return json.loads(b64url_decode(protected_b64))


def jwk_thumbprint(jwk: dict) -> str:
    # RFC 7638 — canonical JSON of required members in lexicographic order
    if jwk["kty"] == "RSA":
        canonical = {"e": jwk["e"], "kty": "RSA", "n": jwk["n"]}
    elif jwk["kty"] == "EC":
        canonical = {"crv": jwk["crv"], "kty": "EC", "x": jwk["x"], "y": jwk["y"]}
    else:
        raise ValueError(f"Unsupported key type: {jwk['kty']}")
    data = json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode()
    return b64url_encode(hashlib.sha256(data).digest())


def _public_key_from_jwk(jwk: dict):
    if jwk["kty"] == "RSA":
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
        return RSAPublicNumbers(e, n).public_key()
    if jwk["kty"] == "EC":
        curves = {"P-256": SECP256R1(), "P-384": SECP384R1(), "P-521": SECP521R1()}
        curve = curves[jwk["crv"]]
        x = int.from_bytes(b64url_decode(jwk["x"]), "big")
        y = int.from_bytes(b64url_decode(jwk["y"]), "big")
        return EllipticCurvePublicNumbers(x, y, curve).public_key()
    raise ValueError(f"Unsupported key type: {jwk['kty']}")


def verify_jws(protected: dict, payload_b64: str, signature_b64: str, jwk: dict, protected_b64: str) -> bool:
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    signature = b64url_decode(signature_b64)
    try:
        public_key = _public_key_from_jwk(jwk)
        alg = protected.get("alg", "")
        if alg.startswith("RS"):
            public_key.verify(signature, signing_input, padding.PKCS1v15(), hashes.SHA256())
        elif alg.startswith("ES"):
            # JWS ES* uses raw r||s; convert to DER for cryptography
            half = len(signature) // 2
            r = int.from_bytes(signature[:half], "big")
            s = int.from_bytes(signature[half:], "big")
            der_sig = utils.encode_dss_signature(r, s)
            hash_alg = {"ES256": hashes.SHA256(), "ES384": hashes.SHA384(), "ES512": hashes.SHA512()}[alg]
            public_key.verify(der_sig, signing_input, ec.ECDSA(hash_alg))
        else:
            return False
        return True
    except (InvalidSignature, ValueError, KeyError):
        return False
