import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings

CA_DIR = os.path.join(settings.BASE_DIR, 'ca_root')
ROOT_KEY_PATH = os.path.join(CA_DIR, 'skysca_root.key')
ROOT_CERT_PATH = os.path.join(CA_DIR, 'skysca_root.crt')

def setup_root_ca():
    """Generates a self-signed Root CA if one doesn't exist."""
    if not os.path.exists(CA_DIR):
        os.makedirs(CA_DIR, exist_ok=True)
        
    if os.path.exists(ROOT_KEY_PATH) and os.path.exists(ROOT_CERT_PATH):
        return # Already setup

    # Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
    )

    # Generate Root Certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Uttarakhand"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Haldwani"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Sky's CA Root Authority"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"Sky's CA Root CA"),
    ])
    
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
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650) # 10 years
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(private_key, hashes.SHA256())

    # Save Private Key
    with open(ROOT_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save Certificate
    with open(ROOT_CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

def sign_csr(csr_pem_bytes):
    """
    Signs a CSR using the Sky's CA Root CA.
    Returns a tuple: (PEM-encoded certificate bytes, serial_number as string)
    """
    setup_root_ca()

    # Load Root CA Private Key
    with open(ROOT_KEY_PATH, "rb") as key_file:
        root_private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )

    # Load Root CA Certificate
    with open(ROOT_CERT_PATH, "rb") as cert_file:
        root_cert = x509.load_pem_x509_certificate(cert_file.read())

    # Load the CSR
    csr = x509.load_pem_x509_csr(csr_pem_bytes)

    # Extract Domain from Common Name for SAN
    domain = None
    for attr in csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
        domain = attr.value
        break

    serial_num = x509.random_serial_number()

    # Build the user's certificate
    cert = x509.CertificateBuilder().subject_name(
        csr.subject
    ).issuer_name(
        root_cert.subject
    ).public_key(
        csr.public_key()
    ).serial_number(
        serial_num
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        # Valid for 1 year
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=False, path_length=None), critical=True,
    ).add_extension(
        x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False
    ).add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(root_private_key.public_key()), critical=False
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=True,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=False,
            crl_sign=False,
            encipher_only=False,
            decipher_only=False
        ), critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([
            x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
            x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
        ]), critical=False
    ).add_extension(
        x509.CRLDistributionPoints([
            x509.DistributionPoint(
                full_name=[x509.UniformResourceIdentifier(settings.CRL_DISTRIBUTION_URL)],
                relative_name=None,
                reasons=None,
                crl_issuer=None,
            )
        ]), critical=False
    )

    # Add SubjectAlternativeName if we have a domain
    if domain:
        cert = cert.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(domain)]),
            critical=False
        )

    # Copy any extensions from the CSR (e.g. if the user provided additional SANs)
    for ext in csr.extensions:
        # Don't duplicate extensions we just added
        if ext.oid not in [x509.OID_BASIC_CONSTRAINTS, x509.OID_SUBJECT_KEY_IDENTIFIER, x509.OID_AUTHORITY_KEY_IDENTIFIER, x509.OID_KEY_USAGE, x509.OID_EXTENDED_KEY_USAGE, x509.OID_SUBJECT_ALTERNATIVE_NAME]:
            cert = cert.add_extension(ext.value, ext.critical)

    # Sign the certificate
    signed_cert = cert.sign(root_private_key, hashes.SHA256())

    # Return (PEM bytes, serial number string)
    return signed_cert.public_bytes(serialization.Encoding.PEM), str(serial_num)

def generate_static_crl():
    """
    Generates a static DER-encoded CRL file and saves it to disk.
    Queries the database for revoked certificates and increments the CRL number.
    """
    setup_root_ca()
    from .models import CertificateRequest, CRLState
    
    # Get or create CRLState
    crl_state, _ = CRLState.objects.get_or_create(id=1)
    
    with open(ROOT_KEY_PATH, "rb") as key_file:
        root_private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    with open(ROOT_CERT_PATH, "rb") as cert_file:
        root_cert = x509.load_pem_x509_certificate(cert_file.read())

    builder = x509.CertificateRevocationListBuilder()
    builder = builder.issuer_name(root_cert.subject)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = builder.last_update(now)
    builder = builder.next_update(now + datetime.timedelta(days=7))

    # Add revoked certificates
    revoked_certs = CertificateRequest.objects.filter(status='revoked', serial_number__isnull=False)
    for cert in revoked_certs:
        reason_flag = x509.ReasonFlags.unspecified
        if cert.revocation_reason:
            try:
                reason_flag = getattr(x509.ReasonFlags, cert.revocation_reason)
            except AttributeError:
                pass
                
        revoked_cert = x509.RevokedCertificateBuilder().serial_number(
            int(cert.serial_number)
        ).revocation_date(
            cert.revoked_at or now
        ).add_extension(
            x509.CRLReason(reason_flag), critical=False
        ).build()
        builder = builder.add_revoked_certificate(revoked_cert)

    # Add CRL extensions
    builder = builder.add_extension(
        x509.CRLNumber(crl_state.current_crl_number), critical=False
    ).add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(root_private_key.public_key()), critical=False
    )

    crl = builder.sign(private_key=root_private_key, algorithm=hashes.SHA256())

    # Save DER encoded CRL to disk
    crl_path = os.path.join(CA_DIR, 'latest.crl')
    with open(crl_path, "wb") as f:
        f.write(crl.public_bytes(serialization.Encoding.DER))

    # Increment CRL Number
    crl_state.current_crl_number += 1
    crl_state.save()
