import pytest
from app.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService()


class TestKeyGeneration:
    def test_generate_rsa_key(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        assert "-----BEGIN RSA PRIVATE KEY-----" in key_pem or "-----BEGIN PRIVATE KEY-----" in key_pem

    def test_generate_ec_key(self, crypto):
        key_pem = crypto.generate_key("EC", 256)
        assert "-----BEGIN EC PRIVATE KEY-----" in key_pem or "-----BEGIN PRIVATE KEY-----" in key_pem

    def test_invalid_algorithm_raises(self, crypto):
        with pytest.raises(ValueError):
            crypto.generate_key("DSA", 2048)


class TestRootCA:
    def test_create_root_ca(self, crypto):
        key_pem = crypto.generate_key("RSA", 2048)
        subject = {"CN": "Test Root CA", "O": "Test Org", "C": "US"}
        cert_pem = crypto.create_root_ca(key_pem, subject, 3650)
        assert "-----BEGIN CERTIFICATE-----" in cert_pem

    def test_root_ca_is_self_signed(self, crypto):
        from cryptography import x509
        key_pem = crypto.generate_key("RSA", 2048)
        subject = {"CN": "Test Root CA", "O": "Test Org", "C": "US"}
        cert_pem = crypto.create_root_ca(key_pem, subject, 3650)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        assert cert.issuer == cert.subject


class TestIntermediateCA:
    def test_create_intermediate_ca(self, crypto):
        root_key = crypto.generate_key("RSA", 2048)
        root_subject = {"CN": "Root CA", "O": "Test", "C": "US"}
        root_cert = crypto.create_root_ca(root_key, root_subject, 3650)
        int_key = crypto.generate_key("RSA", 2048)
        int_subject = {"CN": "Intermediate CA", "O": "Test", "C": "US"}
        int_cert = crypto.create_intermediate_ca(int_key, int_subject, root_cert, root_key, 1825)
        assert "-----BEGIN CERTIFICATE-----" in int_cert

    def test_intermediate_signed_by_root(self, crypto):
        from cryptography import x509
        root_key = crypto.generate_key("RSA", 2048)
        root_subject = {"CN": "Root CA", "O": "Test", "C": "US"}
        root_cert_pem = crypto.create_root_ca(root_key, root_subject, 3650)
        int_key = crypto.generate_key("RSA", 2048)
        int_subject = {"CN": "Intermediate CA", "O": "Test", "C": "US"}
        int_cert_pem = crypto.create_intermediate_ca(int_key, int_subject, root_cert_pem, root_key, 1825)
        root_cert = x509.load_pem_x509_certificate(root_cert_pem.encode())
        int_cert = x509.load_pem_x509_certificate(int_cert_pem.encode())
        assert int_cert.issuer == root_cert.subject


class TestCSRAndSigning:
    def test_generate_and_sign_csr(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_subject = {"CN": "Test CA", "O": "Test", "C": "US"}
        ca_cert = crypto.create_root_ca(ca_key, ca_subject, 3650)
        cert_key = crypto.generate_key("RSA", 2048)
        csr_pem = crypto.generate_csr(cert_key, {"CN": "test.example.com"}, [{"type": "DNS", "value": "test.example.com"}])
        assert "-----BEGIN CERTIFICATE REQUEST-----" in csr_pem
        cert_pem = crypto.sign_csr(csr_pem, ca_cert, ca_key, 365)
        assert "-----BEGIN CERTIFICATE-----" in cert_pem


class TestFormatConversion:
    def test_convert_to_der(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_cert = crypto.create_root_ca(ca_key, {"CN": "Test CA", "O": "Test", "C": "US"}, 365)
        der_bytes = crypto.convert_format(ca_cert, None, "der")
        assert isinstance(der_bytes, bytes)
        assert b"-----BEGIN" not in der_bytes

    def test_convert_to_pkcs12(self, crypto):
        ca_key = crypto.generate_key("RSA", 2048)
        ca_cert = crypto.create_root_ca(ca_key, {"CN": "Test CA", "O": "Test", "C": "US"}, 365)
        p12_bytes = crypto.convert_format(ca_cert, ca_key, "pkcs12", passphrase="test123")
        assert isinstance(p12_bytes, bytes)
