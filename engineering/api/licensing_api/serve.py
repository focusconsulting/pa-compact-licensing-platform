"""Start the API in a deployed container: gunicorn serving TLS (ADR-0019).

The load balancer encrypts its connection to the container but does not validate the
certificate it is shown, so each container makes its own at start. Local development
runs uvicorn over HTTP (``just dev``) and never comes through here.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# In memory: the container's root filesystem is read-only (ecs.tf), and the private key
# never reaches a disk. The container's health check verifies against the certificate here.
TLS_DIR = Path('/dev/shm/licensing-api-tls')

# A task is replaced by the next deploy long before this; nothing checks it either way.
CERTIFICATE_LIFETIME = timedelta(days=365)


def write_certificate(directory: Path) -> tuple[Path, Path]:
    """Write a new private key and a self-signed certificate for ``localhost``; return their paths.

    The certificate is its own issuer, marked as a CA so a client given the file as its
    trust store accepts it under Python's strict X.509 checks.
    """
    directory.mkdir(mode=0o700, exist_ok=True)
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + CERTIFICATE_LIFETIME)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )

    key_path = directory / 'key.pem'
    key_path.touch(mode=0o600)
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    cert_path = directory / 'cert.pem'
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    return cert_path, key_path


def main() -> None:
    """Replace this process with gunicorn, serving TLS on port 8000 with a new certificate."""
    cert_path, key_path = write_certificate(TLS_DIR)
    os.execvp(
        'gunicorn',
        [
            'gunicorn',
            '-k',
            'uvicorn.workers.UvicornWorker',
            '--bind',
            '0.0.0.0:8000',
            '--certfile',
            str(cert_path),
            '--keyfile',
            str(key_path),
            # gunicorn's heartbeat files go to memory too, which is also what its
            # documentation advises in containers.
            '--worker-tmp-dir',
            '/dev/shm',
            # Nothing uses gunicorn's control interface, and its socket would need a
            # writable home directory.
            '--no-control-socket',
            'licensing_api.__main__:app',
        ],
    )


if __name__ == '__main__':
    main()
