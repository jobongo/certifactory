import uuid
from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12 as pkcs12_serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_NAME_OID_MAP = {
    "CN": NameOID.COMMON_NAME,
    "O": NameOID.ORGANIZATION_NAME,
    "OU": NameOID.ORGANIZATIONAL_UNIT_NAME,
    "C": NameOID.COUNTRY_NAME,
    "ST": NameOID.STATE_OR_PROVINCE_NAME,
    "L": NameOID.LOCALITY_NAME,
}

_EC_CURVES = {
    256: ec.SECP256R1(),
    384: ec.SECP384R1(),
    521: ec.SECP521R1(),
}

_KEY_USAGE_MAP = {
    "digital_signature": "digital_signature",
    "key_encipherment": "key_encipherment",
    "data_encipherment": "data_encipherment",
    "key_agreement": "key_agreement",
    "key_cert_sign": "key_cert_sign",
    "crl_sign": "crl_sign",
    "content_commitment": "content_commitment",
}

_EKU_MAP = {
    "server_auth": ExtendedKeyUsageOID.SERVER_AUTH,
    "client_auth": ExtendedKeyUsageOID.CLIENT_AUTH,
    "code_signing": ExtendedKeyUsageOID.CODE_SIGNING,
    "email_protection": ExtendedKeyUsageOID.EMAIL_PROTECTION,
    "ocsp_signing": ExtendedKeyUsageOID.OCSP_SIGNING,
}


class CryptoService:
    def generate_key(self, algorithm: str, key_size: int) -> str:
        if algorithm == "RSA":
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        elif algorithm == "EC":
            curve = _EC_CURVES.get(key_size)
            if curve is None:
                raise ValueError(f"Unsupported EC curve size: {key_size}")
            private_key = ec.generate_private_key(curve)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

        return private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()

    def _load_private_key(self, key_pem: str):
        return serialization.load_pem_private_key(key_pem.encode(), password=None)

    def _build_subject(self, subject: dict) -> x509.Name:
        attrs = []
        for key, value in subject.items():
            oid = _NAME_OID_MAP.get(key)
            if oid:
                attrs.append(x509.NameAttribute(oid, value))
        return x509.Name(attrs)

    def _build_san_extension(self, sans: list[dict]) -> x509.SubjectAlternativeName | None:
        if not sans:
            return None
        names = []
        for san in sans:
            san_type = san["type"]
            value = san["value"]
            if san_type == "DNS":
                names.append(x509.DNSName(value))
            elif san_type == "IP":
                import ipaddress
                names.append(x509.IPAddress(ipaddress.ip_address(value)))
            elif san_type == "Email":
                names.append(x509.RFC822Name(value))
            elif san_type == "URI":
                names.append(x509.UniformResourceIdentifier(value))
        return x509.SubjectAlternativeName(names) if names else None

    def _get_hash_algorithm(self, private_key) -> hashes.HashAlgorithm:
        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            return hashes.SHA256()
        return hashes.SHA256()

    def _next_serial(self) -> int:
        return int(uuid.uuid4().int >> 96)

    def create_root_ca(self, key_pem: str, subject: dict, validity_days: int, max_path_length: int | None = None, extensions: dict | None = None) -> str:
        private_key = self._load_private_key(key_pem)
        subject_name = self._build_subject(subject)
        now = datetime.now(timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(subject_name)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=max_path_length), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False, content_commitment=False, data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(private_key.public_key()), critical=False)
        )
        cert = builder.sign(private_key, self._get_hash_algorithm(private_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def create_intermediate_ca(self, key_pem: str, subject: dict, ca_cert_pem: str, ca_key_pem: str, validity_days: int, max_path_length: int | None = 0, extensions: dict | None = None) -> str:
        private_key = self._load_private_key(key_pem)
        ca_key = self._load_private_key(ca_key_pem)
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        subject_name = self._build_subject(subject)
        now = datetime.now(timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject_name)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=True, path_length=max_path_length), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False, content_commitment=False, data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
            .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        )
        cert = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def generate_csr(self, key_pem: str, subject: dict, sans: list[dict] | None = None) -> str:
        private_key = self._load_private_key(key_pem)
        subject_name = self._build_subject(subject)
        builder = x509.CertificateSigningRequestBuilder().subject_name(subject_name)
        san_ext = self._build_san_extension(sans or [])
        if san_ext:
            builder = builder.add_extension(san_ext, critical=False)
        csr = builder.sign(private_key, self._get_hash_algorithm(private_key))
        return csr.public_bytes(serialization.Encoding.PEM).decode()

    def sign_csr(self, csr_pem: str, ca_cert_pem: str, ca_key_pem: str, validity_days: int, key_usage: list[str] | None = None, extended_key_usage: list[str] | None = None, custom_extensions: list[dict] | None = None) -> str:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        )
        for ext in csr.extensions:
            builder = builder.add_extension(ext.value, critical=ext.critical)
        if key_usage:
            ku_kwargs = {k: False for k in ["digital_signature", "key_encipherment", "content_commitment", "data_encipherment", "key_agreement", "key_cert_sign", "crl_sign", "encipher_only", "decipher_only"]}
            for ku in key_usage:
                mapped = _KEY_USAGE_MAP.get(ku)
                if mapped and mapped in ku_kwargs:
                    ku_kwargs[mapped] = True
            builder = builder.add_extension(x509.KeyUsage(**ku_kwargs), critical=True)
        if extended_key_usage:
            eku_oids = [_EKU_MAP[e] for e in extended_key_usage if e in _EKU_MAP]
            if eku_oids:
                builder = builder.add_extension(x509.ExtendedKeyUsage(eku_oids), critical=False)
        builder = builder.add_extension(x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False)
        builder = builder.add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        cert = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def generate_crl(self, ca_cert_pem: str, ca_key_pem: str, revoked_certs: list[dict], next_update_days: int = 7, crl_number: int = 1) -> str:
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)
        builder = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now)
            .next_update(now + timedelta(days=next_update_days))
            .add_extension(x509.CRLNumber(crl_number), critical=False)
        )
        for entry in revoked_certs:
            revoked = (
                x509.RevokedCertificateBuilder()
                .serial_number(int(entry["serial_number"], 16))
                .revocation_date(entry["revocation_date"])
                .build()
            )
            builder = builder.add_revoked_certificate(revoked)
        crl = builder.sign(ca_key, self._get_hash_algorithm(ca_key))
        return crl.public_bytes(serialization.Encoding.PEM).decode()

    def build_ocsp_response(self, ca_cert_pem: str, signing_key_pem: str, signing_cert_pem: str | None, cert_pem: str, cert_status: str, revocation_time: datetime | None = None) -> bytes:
        from cryptography.x509 import ocsp
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        signing_key = self._load_private_key(signing_key_pem)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        responder_cert = x509.load_pem_x509_certificate(signing_cert_pem.encode()) if signing_cert_pem else ca_cert
        now = datetime.now(timezone.utc)
        if cert_status == "good":
            builder = ocsp.OCSPResponseBuilder().add_response(cert=cert, issuer=ca_cert, algorithm=hashes.SHA256(), cert_status=ocsp.OCSPCertStatus.GOOD, this_update=now, next_update=now + timedelta(hours=1), revocation_time=None, revocation_reason=None)
        elif cert_status == "revoked":
            builder = ocsp.OCSPResponseBuilder().add_response(cert=cert, issuer=ca_cert, algorithm=hashes.SHA256(), cert_status=ocsp.OCSPCertStatus.REVOKED, this_update=now, next_update=now + timedelta(hours=1), revocation_time=revocation_time, revocation_reason=None)
        else:
            return ocsp.OCSPResponseBuilder.build_unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED).public_bytes(serialization.Encoding.DER)
        builder = builder.responder_id(ocsp.OCSPResponderEncoding.HASH, responder_cert)
        response = builder.sign(signing_key, hashes.SHA256())
        return response.public_bytes(serialization.Encoding.DER)

    def convert_format(self, cert_pem: str, key_pem: str | None, fmt: str, passphrase: str | None = None) -> bytes:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        if fmt == "pem":
            return cert.public_bytes(serialization.Encoding.PEM)
        elif fmt == "der":
            return cert.public_bytes(serialization.Encoding.DER)
        elif fmt == "pkcs12":
            private_key = self._load_private_key(key_pem) if key_pem else None
            pw = passphrase.encode() if passphrase else None
            return pkcs12_serialization.serialize_key_and_certificates(name=None, key=private_key, cert=cert, cas=None, encryption_algorithm=(serialization.BestAvailableEncryption(pw) if pw else serialization.NoEncryption()))
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def generate_ocsp_signing_cert(self, ca_cert_pem: str, ca_key_pem: str) -> tuple[str, str]:
        key_pem = self.generate_key("RSA", 2048)
        private_key = self._load_private_key(key_pem)
        ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())
        ca_key = self._load_private_key(ca_key_pem)
        now = datetime.now(timezone.utc)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"OCSP Signing - {ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}")])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(ca_cert.subject)
            .public_key(private_key.public_key())
            .serial_number(self._next_serial())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.KeyUsage(digital_signature=True, key_encipherment=False, content_commitment=False, data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.OCSP_SIGNING]), critical=True)
            .add_extension(x509.OCSPNoCheck(), critical=False)
        )
        cert = builder.sign(ca_key, hashes.SHA256())
        cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        return cert_pem, key_pem

    def parse_csr(self, csr_pem: str) -> dict:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
        subject = {}
        for attr in csr.subject:
            for key, oid in _NAME_OID_MAP.items():
                if attr.oid == oid:
                    subject[key] = attr.value
        sans = []
        try:
            san_ext = csr.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san_ext.value:
                if isinstance(name, x509.DNSName):
                    sans.append({"type": "DNS", "value": name.value})
                elif isinstance(name, x509.IPAddress):
                    sans.append({"type": "IP", "value": str(name.value)})
                elif isinstance(name, x509.RFC822Name):
                    sans.append({"type": "Email", "value": name.value})
                elif isinstance(name, x509.UniformResourceIdentifier):
                    sans.append({"type": "URI", "value": name.value})
        except x509.ExtensionNotFound:
            pass
        return {"subject": subject, "sans": sans}

    def parse_certificate(self, cert_pem: str) -> dict:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        subject = {}
        for attr in cert.subject:
            for key, oid in _NAME_OID_MAP.items():
                if attr.oid == oid:
                    subject[key] = attr.value
        issuer = {}
        for attr in cert.issuer:
            for key, oid in _NAME_OID_MAP.items():
                if attr.oid == oid:
                    issuer[key] = attr.value

        is_ca = False
        try:
            bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            is_ca = bc.value.ca
        except x509.ExtensionNotFound:
            pass

        sans = []
        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            for name in san_ext.value:
                if isinstance(name, x509.DNSName):
                    sans.append({"type": "DNS", "value": name.value})
                elif isinstance(name, x509.IPAddress):
                    sans.append({"type": "IP", "value": str(name.value)})
                elif isinstance(name, x509.RFC822Name):
                    sans.append({"type": "Email", "value": name.value})
                elif isinstance(name, x509.UniformResourceIdentifier):
                    sans.append({"type": "URI", "value": name.value})
        except x509.ExtensionNotFound:
            pass

        key_algorithm = "RSA"
        key_size = 0
        pub = cert.public_key()
        if isinstance(pub, rsa.RSAPublicKey):
            key_algorithm = "RSA"
            key_size = pub.key_size
        elif isinstance(pub, ec.EllipticCurvePublicKey):
            key_algorithm = "EC"
            key_size = pub.key_size

        return {
            "subject": subject,
            "issuer": issuer,
            "subject_dn": cert.subject.rfc4514_string(),
            "issuer_dn": cert.issuer.rfc4514_string(),
            "serial_number": format(cert.serial_number, "x"),
            "not_before": cert.not_valid_before_utc,
            "not_after": cert.not_valid_after_utc,
            "is_ca": is_ca,
            "key_algorithm": key_algorithm,
            "key_size": key_size,
            "sans": sans,
        }

    def load_pkcs12(self, data: bytes, passphrase: str | None = None) -> tuple[str, str, list[str]]:
        from cryptography.hazmat.primitives.serialization import pkcs12
        pw = passphrase.encode() if passphrase else None
        private_key, certificate, chain = pkcs12.load_key_and_certificates(data, pw)
        cert_pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ).decode()
        chain_pems = [c.public_bytes(serialization.Encoding.PEM).decode() for c in (chain or [])]
        return cert_pem, key_pem, chain_pems

    def der_to_pem_cert(self, der_bytes: bytes) -> str:
        cert = x509.load_der_x509_certificate(der_bytes)
        return cert.public_bytes(serialization.Encoding.PEM).decode()

    def der_to_pem_key(self, der_bytes: bytes) -> str:
        key = serialization.load_der_private_key(der_bytes, password=None)
        return key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode()

    def verify_key_matches_cert(self, key_pem: str, cert_pem: str) -> bool:
        key = self._load_private_key(key_pem)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        key_pub_bytes = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        cert_pub_bytes = cert.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return key_pub_bytes == cert_pub_bytes
