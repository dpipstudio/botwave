import datetime
import ipaddress
import tempfile
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def gen_cert():
    # gens a self-signed TLS certificate for runtime encryption
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"BotWave-Server"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"DPIP Studio"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"BotWave"),
    ])
    
    # Build certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    return cert_pem, key_pem


def save_cert(cert_pem, key_pem):
    cert_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.crt')
    cert_file.write(cert_pem)
    cert_file.flush()
    cert_path = cert_file.name
    cert_file.close()
    
    key_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.key')
    key_file.write(key_pem)
    key_file.flush()
    key_path = key_file.name
    key_file.close()
    
    return cert_path, key_path