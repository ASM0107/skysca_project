import os
import django
import sys
from unittest.mock import patch, MagicMock

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skysca.settings')
django.setup()

from caCode.models import CertificateRequest
from caCode.views import run_dns_verification
import dns.resolver

def run_test():
    # 1. Get the latest certificate request (the one we created for example.com)
    cert = CertificateRequest.objects.last()
    if not cert:
        print("No certificate requests found.")
        return
    
    print(f"Testing verification for Domain: {cert.domain}")
    print(f"Initial Status: {cert.status}, Verified: {cert.verified}")
    print(f"Expected DNS Token: {cert.dns_token}")

    # 2. Create a mock DNS answer
    mock_answer = MagicMock()
    # dns.resolver.resolve returns an object where rdata.to_text() returns the TXT value
    mock_rdata = MagicMock()
    mock_rdata.to_text.return_value = f'"{cert.dns_token}"'
    mock_answer.__iter__.return_value = [mock_rdata]

    # 3. Patch dns.resolver.resolve
    with patch('dns.resolver.resolve', return_value=mock_answer) as mock_resolve:
        # Call the unwrapped function if possible, or just the wrapper
        try:
            # django-background-tasks usually exposes the original function via .task_function or we can just call .now()
            # Let's try calling .now() which executes it synchronously.
            run_dns_verification.now(cert.id)
        except AttributeError:
            # If it's not a django-background-task object or now() isn't there, we just call it directly.
            # Some versions of django-background-tasks might not have .now(). Let's import the unwrapped if needed.
            # Wait, we can just call it directly in newer versions, or we can look up the task in DB.
            print("Direct call failed, trying direct execution")
            
    # 4. Reload from DB and check
    cert.refresh_from_db()
    print(f"Final Status: {cert.status}, Verified: {cert.verified}")
    if cert.verified:
        print("SUCCESS! The verification logic worked perfectly.")
    else:
        print("FAILED to verify.")

if __name__ == "__main__":
    run_test()
