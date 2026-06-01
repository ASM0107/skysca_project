from django.db import models
from django.contrib.auth.models import User
import uuid
from django_countries.fields import CountryField
def get_uuid_hex():
    return uuid.uuid4().hex

class CertificateRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending DNS Validation'),
        ('valid', 'Validated'),
        ('rejected', 'Rejected'),
        ('issued', 'Certificate Issued'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    domain = models.CharField(max_length=255)
    csr = models.FileField(upload_to='csrs/')
    certificate = models.FileField(upload_to='certificates/', null=True, blank=True)
    dns_token = models.CharField(max_length=64, default=get_uuid_hex)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified = models.BooleanField(default=False)
    
    # Lifecycle & Revocation
    revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revocation_reason = models.CharField(max_length=50, null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    serial_number = models.CharField(max_length=128, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def dns_record_name(self):
        return f"_skysca.{self.domain}"

    def dns_record_value(self):
        return self.dns_token

    def __str__(self):
        return f"{self.domain} - {self.status}"

class CRLState(models.Model):
    current_crl_number = models.BigIntegerField(default=1)
    last_generated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"CRL Number: {self.current_crl_number}"
