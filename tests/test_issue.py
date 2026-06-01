import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skysca.settings')
django.setup()

from django.contrib.auth.models import User

from caCode.models import CertificateRequest

def run_test():
    # 1. Get the verified certificate request for example.com
    cert = CertificateRequest.objects.filter(domain='example.com', verified=True).last()
    if not cert:
        print("No verified certificate request found for example.com.")
        return

    print(f"Testing issuance for Domain: {cert.domain}, Status: {cert.status}")
    
    # 1.5 Generate a valid CSR using cryptography to replace the one from the buggy frontend
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from django.core.files.base import ContentFile
    
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr_builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, u"example.com")])
    )
    csr_obj = csr_builder.sign(key, hashes.SHA256())
    csr_bytes = csr_obj.public_bytes(serialization.Encoding.PEM)
    
    cert.csr.save("valid_example_com.csr", ContentFile(csr_bytes))
    cert.save()
    
    # 2. Get the user
    user = cert.user
    
    # 3. Simulate client login and POST request
    client = Client()
    client.force_login(user)
    
    response = client.post(f'/issue-certificate/{cert.id}/', SERVER_NAME='localhost')
    print(f"Response Status: {response.status_code}")
    print(f"Redirect URL: {response.url if response.status_code == 302 else 'No redirect'}")
    
    # 4. Reload from DB
    cert.refresh_from_db()
    print(f"Final Status: {cert.status}")
    
    if cert.status == 'issued' and cert.certificate:
        print(f"SUCCESS! Certificate saved to: {cert.certificate.name}")
        
        # Verify the root CA was created
        ca_dir = os.path.join(django.conf.settings.BASE_DIR, 'ca_root')
        print(f"Root CA Key exists: {os.path.exists(os.path.join(ca_dir, 'apnassl_root.key'))}")
        print(f"Root CA Cert exists: {os.path.exists(os.path.join(ca_dir, 'apnassl_root.crt'))}")
    else:
        print("FAILED to issue certificate.")

if __name__ == "__main__":
    run_test()
