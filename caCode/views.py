from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import SignUpForm, LoginForm, CSRUploadForm
from .models import CertificateRequest
import secrets
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import SignUpForm, LoginForm, CSRUploadForm
from .models import CertificateRequest
import secrets, io, zipfile, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import secrets
from django_ratelimit.decorators import ratelimit

@login_required(login_url='login')
@ratelimit(key='ip', rate='5/m', block=True)
def generate_csr(request):
    if request.method == "POST":
        csr_pem = request.POST.get("csr")
        
        if not csr_pem:
            return JsonResponse({"error": "Missing CSR"}, status=400)

        # Parse CSR strictly to extract domain
        try:
            csr_obj = x509.load_pem_x509_csr(csr_pem.encode('utf-8'))
            common_name = None
            for attr in csr_obj.subject.get_attributes_for_oid(NameOID.COMMON_NAME):
                common_name = attr.value
                break
            
            if not common_name:
                return JsonResponse({"error": "CSR missing Common Name (Domain)"}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Invalid CSR: {str(e)}"}, status=400)

        from django.core.files.base import ContentFile
        csr_filename = f"{common_name}_csr.pem"
        csr_file = ContentFile(csr_pem, name=csr_filename)
        
        # We assume models.py will handle the uuid default appropriately.
        cert_request = CertificateRequest.objects.create(
            user=request.user,
            domain=common_name,
            status='pending',
            verified=False
        )
        cert_request.csr.save(csr_filename, csr_file)
        
        return JsonResponse({"message": "CSR saved successfully", "redirect": "/domain-verification/"})

    return JsonResponse({"error": "Invalid request"}, status=400)

def homepage(request):
    return render(request, 'caCode/homepage.html')

def about(request):
    return render(request, 'caCode/about.html')

def dashboard(request):
    if request.user.is_authenticated:
        certificates = CertificateRequest.objects.filter(user=request.user)
    else:
        certificates = []
    return render(request, 'caCode/dashboard.html', {'certificates': certificates})

def support(request):
    return render(request, 'caCode/support.html')

def auto_renewal(request):
    return render(request, 'caCode/auto-renewal.html')

def certificate_generator(request):
    return render(request, 'caCode/certificate-generator.html')

@login_required(login_url='login')
def certificates(request):
    return render(request, 'caCode/certificates.html')

from django.views.decorators.http import require_POST
from background_task import background
import dns.resolver
import logging

logger = logging.getLogger(__name__)

@background(schedule=1)
def run_dns_verification(cert_id):
    from .models import CertificateRequest
    try:
        cert = CertificateRequest.objects.get(id=cert_id)
        txt_name = cert.dns_record_name()
        answers = dns.resolver.resolve(txt_name, 'TXT')
        for rdata in answers:
            txt_value = rdata.to_text().strip('"')
            if cert.dns_token == txt_value:
                cert.verified = True
                cert.status = 'valid'
                cert.save()
                break
    except CertificateRequest.DoesNotExist:
        logger.error(f"CertificateRequest with id {cert_id} not found.")
    except dns.resolver.NXDOMAIN:
        logger.warning(f"NXDOMAIN for _apnassl.{cert.domain}")
    except dns.resolver.NoAnswer:
        logger.warning(f"No TXT records found for _apnassl.{cert.domain}")
    except dns.resolver.Timeout:
        logger.warning(f"Timeout resolving _apnassl.{cert.domain}")
    except Exception as e:
        logger.error(f"Unexpected error resolving DNS: {e}")

def domain_verification(request):
    if request.user.is_superuser:
        certificates = CertificateRequest.objects.all()
    else:
        certificates = CertificateRequest.objects.filter(user=request.user)
    return render(request, 'caCode/dns-verification.html', {'certificates': certificates})

@require_POST
def verify_dns(request, cert_id):
    from django.shortcuts import get_object_or_404
    cert = get_object_or_404(CertificateRequest, id=cert_id, user=request.user)
    
    run_dns_verification(cert.id)
    messages.info(request, "DNS verification queued. Please refresh in a few moments.")
    return redirect('domain_verification')

def installation_guides(request):
    return render(request, 'caCode/installation-guides.html')

def key_generator(request):
    return render(request, 'caCode/key-generator.html')

def organization_validation(request):
    return render(request, 'caCode/organization-validation.html')

def revocation(request):
    return render(request, 'caCode/revocation.html')


# Auth views
from .ca_core import sign_csr
from django.core.files.base import ContentFile

@require_POST
@login_required(login_url='login')
def issue_certificate(request, cert_id):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponseBadRequest
    from django.utils import timezone
    cert = get_object_or_404(CertificateRequest, id=cert_id, user=request.user)

    if not cert.verified:
        messages.error(request, "Domain is not verified yet.")
        return redirect('dashboard')

    if cert.status == 'issued':
        return HttpResponseBadRequest("Certificate already issued")

    try:
        # Sign the CSR
        csr_bytes = cert.csr.read()
        cert_pem_bytes, serial_number = sign_csr(csr_bytes)

        # Save to the certificate field
        cert_filename = f"{cert.domain}_certificate.crt"
        cert.certificate.save(cert_filename, ContentFile(cert_pem_bytes))

        # Update status
        cert.status = 'issued'
        cert.serial_number = serial_number
        cert.issued_at = timezone.now()
        cert.expires_at = timezone.now() + datetime.timedelta(days=365)
        cert.save()
        messages.success(request, f"Certificate successfully issued for {cert.domain}!")

    except Exception as e:
        logger.error(f"Failed to issue certificate for {cert.domain}: {e}")
        messages.error(request, "An error occurred while issuing the certificate. Please contact support.")

    return redirect('dashboard')

@require_POST
@login_required(login_url='login')
def revoke_certificate(request, cert_id):
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    from .ca_core import generate_static_crl
    
    cert = get_object_or_404(CertificateRequest, id=cert_id, user=request.user)

    if cert.status != 'issued':
        messages.error(request, "Only issued certificates can be revoked.")
        return redirect('dashboard')

    reason = request.POST.get('revocation_reason', 'unspecified')
    
    cert.status = 'revoked'
    cert.revoked = True
    cert.revoked_at = timezone.now()
    cert.revocation_reason = reason
    cert.save()

    try:
        generate_static_crl()
        messages.success(request, f"Certificate for {cert.domain} has been securely revoked.")
    except Exception as e:
        logger.error(f"Failed to generate CRL after revocation: {e}")
        messages.warning(request, f"Certificate revoked, but CRL generation failed: {e}")

    return redirect('dashboard')

def download_crl(request):
    from django.http import HttpResponse, Http404
    import os
    from django.conf import settings
    from .ca_core import generate_static_crl
    
    crl_path = os.path.join(settings.BASE_DIR, 'ca_root', 'latest.crl')
    if not os.path.exists(crl_path):
        try:
            generate_static_crl()
        except Exception:
            raise Http404("CRL not available")

    with open(crl_path, "rb") as f:
        crl_bytes = f.read()

    response = HttpResponse(crl_bytes, content_type='application/pkix-crl')
    response['Cache-Control'] = 'public, max-age=3600'
    return response

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully.')
            return redirect('login')
        else:
            messages.error(request, 'Form invalid.')
    else:
        form = SignUpForm()
    return render(request, 'caCode/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('certificates')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'caCode/login.html')


@ratelimit(key='ip', rate='5/m', block=True)
def upload_csr(request):
    if request.method == 'POST':
        form = CSRUploadForm(request.POST)
        if form.is_valid():
            domain = form.cleaned_data['domain']
            csr = form.cleaned_data['csr']
            token = secrets.token_urlsafe(16)

            CertificateRequest.objects.create(
                user=request.user,
                domain=domain,
                csr=csr,
                dns_token=token
            )
            return redirect('dns_verification_list')
    else:
        form = CSRUploadForm()
    return render(request, 'upload_csr.html', {'form': form})
