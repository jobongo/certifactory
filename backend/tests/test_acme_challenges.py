import hashlib
from unittest.mock import patch, MagicMock

from app.services.acme_challenges import key_authorization, dns_txt_value, validate_http_01, validate_dns_01
from app.services.acme_jws import jwk_thumbprint, b64url_encode

JWK = {"kty": "RSA", "n": "abc", "e": "AQAB"}


def test_key_authorization_format():
    ka = key_authorization("mytoken", JWK)
    assert ka == f"mytoken.{jwk_thumbprint(JWK)}"


def test_dns_txt_value_is_sha256_of_key_auth():
    ka = key_authorization("mytoken", JWK)
    expected = b64url_encode(hashlib.sha256(ka.encode()).digest())
    assert dns_txt_value("mytoken", JWK) == expected


def test_validate_http_01_success():
    ka = key_authorization("tok", JWK)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = ka
    with patch("app.services.acme_challenges.httpx.get", return_value=mock_resp):
        assert validate_http_01("example.com", "tok", JWK) is True


def test_validate_http_01_wrong_content():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "wrong"
    with patch("app.services.acme_challenges.httpx.get", return_value=mock_resp):
        assert validate_http_01("example.com", "tok", JWK) is False


def test_validate_dns_01_success():
    expected = dns_txt_value("tok", JWK)
    mock_answer = MagicMock()
    mock_answer.strings = [expected.encode()]
    with patch("app.services.acme_challenges.dns.resolver.resolve", return_value=[mock_answer]):
        assert validate_dns_01("example.com", "tok", JWK) is True


def test_validate_dns_01_no_match():
    mock_answer = MagicMock()
    mock_answer.strings = [b"some-other-value"]
    with patch("app.services.acme_challenges.dns.resolver.resolve", return_value=[mock_answer]):
        assert validate_dns_01("example.com", "tok", JWK) is False
