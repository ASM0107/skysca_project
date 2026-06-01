# caCode Django App

The `caCode` app is the main application module for the ApnaSSL Certificate Authority (CA) platform. It provides core functionality for digital certificate management, user workflows, and frontend integration.

## Features

- Certificate Request and Management
- Key Generation Tools
- Domain Verification (DNS, HTTP, TXT)
- Organization Validation Workflow
- Certificate Revocation and Auto-renewal
- User Authentication and Management
- Database Models for Certificate Records
- Admin Interface for CA Operations
- Interactive Frontend Templates

## Directory Structure

```
caCode/
├── __init__.py
├── admin.py                # Django admin customizations
├── apps.py                 # App configuration
├── forms.py                # Django forms for user input
├── models.py               # Database models (CertificateRequest, etc.)
├── tests.py                # Unit tests
├── urls.py                 # URL routing for the app
├── views.py                # View logic (certificate issuance, verification, etc.)
├── migrations/             # Database migrations
│   ├── __init__.py
│   ├── 0001_initial.py
│   ├── ... (other migration files)
├── static/
│   ├── images/
│   │   └── ApnaSSL.png
│   └── js/
│       └── homepage.js
└── templates/
    └── caCode/
        ├── about.html
        ├── auto-renewal.html
        ├── certificate-generator.html
        ├── certificates.html
        ├── dashboard.html
        ├── Database.html
        ├── dns-verification.html
        ├── domain-verification.html
        ├── homepage.html
        ├── installation-guides.html
        ├── key-generator.html
        ├── login.html
        ├── organization-validation.html
        ├── revocation.html
        ├── signup.html
        └── support.html
```

## Key Modules

- `models.py`: Defines database models for certificate requests, user profiles, and related CA entities.
- `views.py`: Implements business logic for certificate issuance, verification, revocation, and user workflows.
- `forms.py`: Contains Django forms for user input and validation.
- `admin.py`: Customizes the Django admin interface for CA operations.
- `urls.py`: Maps URLs to views for the app.
- `static/`: Contains static assets (images, JavaScript).
- `templates/caCode/`: HTML templates for all user-facing pages and workflows.

## Frontend Templates

- Dashboard: `dashboard.html`
- Certificate Generator: `certificate-generator.html`
- Key Generator: `key-generator.html`
- Domain Verification: `domain-verification.html`, `dns-verification.html`
- Organization Validation: `organization-validation.html`
- Revocation & Auto-renewal: `revocation.html`, `auto-renewal.html`
- User Authentication: `login.html`, `signup.html`
- Support & Guides: `support.html`, `installation-guides.html`
- About: `about.html`
- Homepage: `homepage.html`

## Usage

The `caCode` app is integrated into the main Django project (`apnasslproject`). All certificate authority workflows, user interactions, and frontend pages are managed through this app.

## License

This project is licensed under the MIT License.

## Contact

Maintainer: [@ASM0107](https://github.com/ASM0107),[@Sauravnegiii](https://github.com/Sauravnegiii)
Project Link: [https://github.com/ASM0107/CA](https://github.com/ASM0107/CA)
