import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
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
    sig = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = b64url_encode(sig)
    tampered = b64url_encode(json.dumps({"a": 2}).encode())
    assert verify_jws(protected, tampered, sig_b64, jwk, protected_b64=protected_b64) is False


def _ec_jwk(public_key):
    nums = public_key.public_numbers()
    def coord_b64(n):
        b = n.to_bytes(32, "big")
        return b64url_encode(b)
    return {"kty": "EC", "crv": "P-256", "x": coord_b64(nums.x), "y": coord_b64(nums.y)}


def test_verify_jws_ec_p256_round_trip():
    key = ec.generate_private_key(SECP256R1())
    jwk = _ec_jwk(key.public_key())
    protected = {"alg": "ES256", "nonce": "n2", "url": "https://x/acme/new-order"}
    payload = {"identifiers": [{"type": "dns", "value": "example.com"}]}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(json.dumps(payload).encode())
    signing_input = f"{protected_b64}.{payload_b64}".encode()
    der_sig = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    sig_b64 = b64url_encode(raw_sig)
    assert verify_jws(protected, payload_b64, sig_b64, jwk, protected_b64=protected_b64) is True


def test_verify_jws_rejects_alg_none():
    protected = {"alg": "none", "nonce": "n3", "url": "https://x"}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(b"anything")
    sig_b64 = b64url_encode(b"fakesig")
    jwk = {"kty": "RSA", "n": b64url_encode(b"\x00" * 256), "e": b64url_encode((65537).to_bytes(3, "big"))}
    assert verify_jws(protected, payload_b64, sig_b64, jwk, protected_b64=protected_b64) is False


def test_verify_jws_malformed_base64_signature():
    protected = {"alg": "RS256", "nonce": "n4", "url": "https://x"}
    protected_b64 = b64url_encode(json.dumps(protected).encode())
    payload_b64 = b64url_encode(b"payload")
    jwk = {"kty": "RSA", "n": b64url_encode(b"\x00" * 256), "e": b64url_encode((65537).to_bytes(3, "big"))}
    assert verify_jws(protected, payload_b64, "!!!not-base64!!!", jwk, protected_b64=protected_b64) is False
