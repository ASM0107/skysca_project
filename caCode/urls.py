from django.urls import path
from . import views
urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('about/', views.about, name='about'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('support/', views.support, name='support'),
    path('auto-renewal/', views.auto_renewal, name='auto_renewal'),
    path('certificate-generator/', views.certificate_generator, name='certificate_generator'),
    path('certificates/', views.certificates, name='certificates'),
    path('domain-verification/', views.domain_verification, name='domain_verification'),
    path('installation-guides/', views.installation_guides, name='installation_guides'),
    path('key-generator/', views.key_generator, name='key_generator'),
    path('organization-validation/', views.organization_validation, name='organization_validation'),
    path('revocation/', views.revocation, name='revocation'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("generate-csr/", views.generate_csr, name="generate_csr"),
    path('verify-dns/<int:cert_id>/', views.verify_dns, name='verify_dns'),
    path('issue-certificate/<int:cert_id>/', views.issue_certificate, name='issue_certificate'),
    path('revoke-certificate/<int:cert_id>/', views.revoke_certificate, name='revoke-certificate'),
    path('download-crl/', views.download_crl, name='download-crl'),
]
