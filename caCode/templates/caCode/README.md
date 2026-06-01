
# caCode Templates Overview

This directory contains the HTML templates for the ApnaSSL Certificate Authority (CA) platform. Each template supports a specific user workflow or feature in the CA web application.

## Template List & Purpose

- `about.html`: Information about the CA platform and its mission.
- `auto-renewal.html`: Manage and view auto-renewal settings for certificates.
- `certificate-generator.html`: Interface for generating digital certificates.
- `certificates.html`: List and manage issued certificates.
- `dashboard.html`: Main user dashboard for certificate management and status overview.
- `Database.html`: Database management and record viewing interface.
- `dns-verification.html`: DNS-based domain verification workflow.
- `domain-verification.html`: General domain verification process.
- `homepage.html`: Landing page for the CA platform.
- `installation-guides.html`: Step-by-step guides for installing certificates and related software.
- `key-generator.html`: Generate cryptographic key pairs for certificate requests.
- `login.html`: User login page.
- `organization-validation.html`: Organization validation workflow for OV/EV certificates.
- `revocation.html`: Manage certificate revocation requests.
- `signup.html`: User registration page.
- `support.html`: Support resources and contact information.

## Usage

These templates are rendered by Django views in the `caCode` app. They provide the frontend for all major certificate authority workflows, including certificate requests, domain and organization validation, revocation, and user management.

Static assets (images, JavaScript) referenced in these templates are located in the `static/` directory of the app.

## Customization

You can modify these templates to change the look, feel, or content of the CA platform. For custom workflows, create new templates in this directory and update the corresponding Django views.

## License

This project is licensed under the MIT License.

*This README provides an overview of the frontend files and their functionality in the CA project.*
