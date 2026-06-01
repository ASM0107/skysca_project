import os
import django
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skysca.settings')
django.setup()

from caCode.models import CertificateRequest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.core.files.base import ContentFile
from django.test import Client
from django.contrib.auth.models import User

def run_test():
    # 1. Create a dummy user
    user, _ = User.objects.get_or_create(username='ext_test_user')
    user.set_password('password123')
    user.save()

    # 2. Create a fresh CSR for testdomain.com
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"testdomain.com")])
    )
    csr_obj = csr_builder.sign(key, hashes.SHA256())
    csr_bytes = csr_obj.public_bytes(serialization.Encoding.PEM)

    # 3. Simulate the generate_csr view (Phase 2 strict parsing)
    client = Client()
    client.force_login(user)
    
    # Send only CSR string, NO commonName
    response = client.post('/generate-csr/', {'csr': csr_bytes.decode('utf-8')}, SERVER_NAME='localhost')
    print(f"Generate CSR View Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Generate CSR failed: {response.content}")
        return

    # 4. Fetch the generated CertificateRequest
    cert = CertificateRequest.objects.filter(user=user).last()
    print(f"Extracted Domain: {cert.domain}")
    if cert.domain != "testdomain.com":
        print("ERROR: Domain extraction failed!")
        return

    # 5. Mark as verified and issue certificate
    cert.verified = True
    cert.status = 'valid'
    cert.save()

    response = client.post(f'/issue-certificate/{cert.id}/', SERVER_NAME='localhost')
    print(f"Issue Cert View Status: {response.status_code}")

    cert.refresh_from_db()
    print(f"Final Status: {cert.status}")
    print(f"Serial Number in DB: {cert.serial_number}")
    print(f"Issued At: {cert.issued_at}")
    print(f"Expires At: {cert.expires_at}")

    if not cert.certificate:
        print("ERROR: Certificate was not saved!")
        return

    # 6. Parse the generated certificate and verify extensions
    cert_bytes = cert.certificate.read()
    parsed_cert = x509.load_pem_x509_certificate(cert_bytes)
    
    print("\n--- X.509 Extensions Verification ---")
    extensions = parsed_cert.extensions
    
    def check_ext(oid_class, name):
        try:
            ext = extensions.get_extension_for_class(oid_class)
            print(f"SUCCESS: Found {name}")
            return ext
        except x509.ExtensionNotFound:
            print(f"FAILED: Missing {name}")
            return None

    san = check_ext(x509.SubjectAlternativeName, "Subject Alternative Name (SAN)")
    if san:
        print(f"  SAN Values: {san.value}")
    
    check_ext(x509.SubjectKeyIdentifier, "Subject Key Identifier (SKI)")
    check_ext(x509.AuthorityKeyIdentifier, "Authority Key Identifier (AKI)")
    check_ext(x509.KeyUsage, "Key Usage")
    check_ext(x509.ExtendedKeyUsage, "Extended Key Usage")

if __name__ == "__main__":
    run_test()
