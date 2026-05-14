import pytest
from app.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService()


@pytest.fixture
def root_ca(crypto):
    key = crypto.generate_key("RSA", 2048)
    cert = crypto.create_root_ca(key, {"CN": "Test Root CA", "O": "Test", "C": "US"}, 3650)
    return cert, key


class TestParseCertificate:
    def test_parse_pem_certificate(self, crypto, root_ca):
        cert_pem, _ = root_ca
        result = crypto.parse_certificate(cert_pem)
        assert result["subject"]["CN"] == "Test Root CA"
        assert result["issuer"]["CN"] == "Test Root CA"
        assert result["is_ca"] is True
        assert "serial_number" in result
        assert "not_before" in result
        assert "not_after" in result
        assert "key_algorithm" in result

    def test_parse_end_entity_cert(self, crypto, root_ca):
        ca_cert, ca_key = root_ca
        ee_key = crypto.generate_key("RSA", 2048)
        csr = crypto.generate_csr(ee_key, {"CN": "test.example.com"}, [{"type": "DNS", "value": "test.example.com"}])
        ee_cert = crypto.sign_csr(csr, ca_cert, ca_key, 365)
        result = crypto.parse_certificate(ee_cert)
        assert result["subject"]["CN"] == "test.example.com"
        assert result["is_ca"] is False
        assert len(result["sans"]) == 1


class TestDERConversion:
    def test_der_to_pem_cert(self, crypto, root_ca):
        cert_pem, _ = root_ca
        der_bytes = crypto.convert_format(cert_pem, None, "der")
        converted_pem = crypto.der_to_pem_cert(der_bytes)
        assert "-----BEGIN CERTIFICATE-----" in converted_pem
        parsed = crypto.parse_certificate(converted_pem)
        assert parsed["subject"]["CN"] == "Test Root CA"

    def test_der_to_pem_key(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        from cryptography.hazmat.primitives import serialization
        key_obj = serialization.load_pem_private_key(key_pem.encode(), password=None)
        der_bytes = key_obj.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        converted_pem = crypto.der_to_pem_key(der_bytes)
        assert "-----BEGIN PRIVATE KEY-----" in converted_pem


class TestKeyVerification:
    def test_matching_key(self, crypto, root_ca):
        cert_pem, key_pem = root_ca
        assert crypto.verify_key_matches_cert(key_pem, cert_pem) is True

    def test_mismatched_key(self, crypto, root_ca):
        cert_pem, _ = root_ca
        other_key = crypto.generate_key("RSA", 2048)
        assert crypto.verify_key_matches_cert(other_key, cert_pem) is False


class TestLoadPKCS12:
    def test_load_pkcs12(self, crypto, root_ca):
        cert_pem, key_pem = root_ca
        p12_bytes = crypto.convert_format(cert_pem, key_pem, "pkcs12", passphrase="test123")
        loaded_cert, loaded_key, chain = crypto.load_pkcs12(p12_bytes, "test123")
        assert "-----BEGIN CERTIFICATE-----" in loaded_cert
        assert "-----BEGIN" in loaded_key
        assert crypto.verify_key_matches_cert(loaded_key, loaded_cert) is True
