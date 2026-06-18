import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization, hashes

from app.services.acme_jws import jwk_thumbprint, verify_jws, decode_protected, b64url_encode, b64url_decode


def _rsa_jwk(public_key):
    nums = public_key.public_numbers()
    def to_b64(n):
        b = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return b64url_encode(b)
    return {"kty": "RSA", "n": to_b64(nums.n), "e": to_b64(nums.e)}


def test_b64url_roundtrip():
    assert b64url_decode(b64url_encode(b"hello")) == b"hello"


def test_jwk_thumbprint_is_stable():
    jwk = {"kty": "RSA", "n": "abc", "e": "AQAB"}
    t1 = jwk_thumbprint(jwk)
    t2 = jwk_thumbprint(jwk)
    assert t1 == t2
    assert "=" not in t1  # no padding


def test_verify_jws_accepts_valid_signature():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    protected = {"alg": "RS256", "nonce": "n1", "url": "https://x/acme/new-order"}
    payload = {"identifiers": [{"type": "dns", "value": "example.com"}]}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    from cryptography.hazmat.primitives.asymmetric import padding
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = b64url_encode(sig)
    assert verify_jws(protected, payload_b64, sig_b64, jwk, protected_b64=protected_b64) is True


def test_verify_jws_rejects_tampered_payload():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = _rsa_jwk(key.public_key())
    protected = {"alg": "RS256", "nonce": "n1", "url": "https://x"}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps({"a": 1}).encode())
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    from cryptography.hazmat.primitives.asymmetric import padding
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = b64url_encode(sig)
    tampered = b64url_encode(json.dumps({"a": 2}).encode())
    assert verify_jws(protected, tampered, sig_b64, jwk, protected_b64=protected_b64) is False
