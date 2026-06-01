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
from caCode.ca_core import ROOT_KEY_PATH, ROOT_CERT_PATH, CA_DIR

def run_test():
    # 1. Get the existing test user and certificate
    user = User.objects.get(username='ext_test_user')
    cert = CertificateRequest.objects.filter(user=user).last()
    
    if not cert:
        print("ERROR: No issued certificate found. Please run test_extensions.py first.")
        return

    # Reset to issued for testing
    cert.status = 'issued'
    cert.revoked = False
    cert.save()

    print(f"Found issued certificate for domain: {cert.domain}, Serial: {cert.serial_number}")

    # 2. Revoke the certificate
    client = Client()
    client.force_login(user)
    
    response = client.post(f'/revoke-certificate/{cert.id}/', {'revocation_reason': 'key_compromise'}, SERVER_NAME='localhost')
    print(f"Revoke View Status: {response.status_code}")

    cert.refresh_from_db()
    print(f"New Status in DB: {cert.status}")
    print(f"Revoked At: {cert.revoked_at}")
    print(f"Revocation Reason: {cert.revocation_reason}")

    if cert.status != 'revoked':
        print("ERROR: Certificate was not revoked in DB!")
        return

    # 3. Download the CRL
    response = client.get('/download-crl/', SERVER_NAME='localhost')
    print(f"Download CRL View Status: {response.status_code}")
    print(f"Content-Type: {response['Content-Type']}")
    print(f"Cache-Control: {response['Cache-Control']}")

    if response.status_code != 200:
        print("ERROR: Failed to download CRL!")
        return

    # 4. Parse the CRL
    crl_bytes = response.content
    parsed_crl = x509.load_der_x509_crl(crl_bytes)
    
    print("\n--- CRL Verification ---")
    print(f"Issuer: {parsed_crl.issuer}")
    print(f"Last Update: {parsed_crl.last_update_utc}")
    print(f"Next Update: {parsed_crl.next_update_utc}")

    # Check Extensions
    try:
        crl_num_ext = parsed_crl.extensions.get_extension_for_class(x509.CRLNumber)
        print(f"SUCCESS: Found CRLNumber ({crl_num_ext.value.crl_number})")
    except x509.ExtensionNotFound:
        print("FAILED: Missing CRLNumber")

    try:
        aki_ext = parsed_crl.extensions.get_extension_for_class(x509.AuthorityKeyIdentifier)
        print("SUCCESS: Found AuthorityKeyIdentifier")
    except x509.ExtensionNotFound:
        print("FAILED: Missing AuthorityKeyIdentifier")

    # Find the revoked cert in the CRL
    revoked_entry = parsed_crl.get_revoked_certificate_by_serial_number(int(cert.serial_number))
    if revoked_entry:
        print(f"SUCCESS: Found serial number {cert.serial_number} in CRL")
        try:
            reason_ext = revoked_entry.extensions.get_extension_for_class(x509.CRLReason)
            print(f"SUCCESS: Revocation Reason: {reason_ext.value.reason.name}")
        except x509.ExtensionNotFound:
            print("FAILED: Missing CRLReason")
    else:
        print("FAILED: Certificate serial number NOT found in CRL!")

if __name__ == "__main__":
    run_test()
