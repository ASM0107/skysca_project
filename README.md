<div align="center">
  <img src="caCode/static/img/logo.png" alt="Sky's CA Logo" width="120" />

  <h1>Sky's CA</h1>

  <p><strong>Enterprise-Grade Internal Public Key Infrastructure &amp; Certificate Authority</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Django-4.2+-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
    <img src="https://img.shields.io/badge/PostgreSQL-Ready-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
    <img src="https://img.shields.io/badge/Railway-Deploy-0B0D0E?style=for-the-badge&logo=railway&logoColor=white" alt="Railway"/>
    <img src="https://img.shields.io/badge/X.509-v3-00CC00?style=for-the-badge" alt="X.509 v3"/>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  </p>
</div>

---

## Overview

**Sky's CA** is a full-stack, production-grade **Private Certificate Authority (CA)** built on Django. It implements the complete certificate lifecycle — from domain ownership verification and CSR parsing, through cryptographic signing with a self-managed Root CA, to certificate revocation and offline CRL distribution.

It is architected to closely mirror the internal PKI workflows used by commercial CAs (Let's Encrypt, DigiCert), making it an excellent foundation for internal tooling, lab environments, private networks, or learning real-world PKI design.

The project prioritizes **security by design** at every layer: DNS-based domain validation, extracted domain names from CSR subjects (not trusting user-supplied form data), duplicate issuance prevention, static CRL artifact generation, and a strict `.gitignore` that prevents private keys from ever reaching version control.

---

## Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Certificate Lifecycle](#-certificate-lifecycle)
- [API Reference](#-api--url-reference)
- [Data Models](#-data-models)
- [Cryptographic Engine](#-cryptographic-engine-ca_corepy)
- [Security Design](#-security-design)
- [CRL Infrastructure](#-certificate-revocation-list-crl-infrastructure)
- [Local Development](#-local-development)
- [Railway Deployment](#-railway-deployment)
- [Environment Variables](#-environment-variables)
- [Project Structure](#-project-structure)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Self-Signed Root CA** | Auto-generates a 4096-bit RSA Root CA on first run with a configurable identity |
| **CSR Upload & Parsing** | Accepts PEM-encoded CSRs; extracts domain from the CSR Subject (never trusts form input) |
| **DNS-01 Domain Validation** | Generates unique per-request DNS TXT tokens (`_skysca.<domain>`) verified asynchronously |
| **X.509 v3 Certificate Issuance** | Issues certificates with full extension suite: `BasicConstraints`, `SubjectKeyIdentifier`, `AuthorityKeyIdentifier`, `KeyUsage`, `ExtendedKeyUsage`, `SubjectAlternativeName`, `CRLDistributionPoints` |
| **In-Browser Key Generation** | Generates RSA 2048/4096-bit or EC key pairs and CSRs entirely client-side using the Web Crypto API |
| **Duplicate Issuance Prevention** | Blocks re-issuance of already-issued certificates with an explicit HTTP 400 guard |
| **Certificate Revocation** | Supports 9 RFC 5280 revocation reasons: `key_compromise`, `ca_compromise`, `affiliation_changed`, `superseded`, `cessation_of_operation`, `certificate_hold`, `remove_from_crl`, `privilege_withdrawn`, `aa_compromise` |
| **Static CRL Distribution** | Generates a DER-encoded CRL file once on revocation; serves it statically from `/download-crl/` — no live key operations per request |
| **Monotonic CRL Numbering** | `CRLState` model enforces monotonically increasing CRL numbers, a hard X.509 RFC requirement |
| **Rate Limiting** | IP-based rate limiting on CSR submission and key generation endpoints (`5/min`) |
| **Background DNS Workers** | Async DNS verification via `django-background-tasks`, decoupled from the request/response cycle |
| **Modern Dark UI** | Glassmorphic dashboard with real-time certificate status, expiry tracking, and one-click actions |
| **PostgreSQL + Railway Ready** | Full production configuration: `dj_database_url`, `whitenoise`, `gunicorn`, `Procfile` |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Sky's CA                              │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  Django App  │    │  ca_core.py │    │   PostgreSQL DB  │  │
│  │  (caCode)    │───▶│  PKI Engine │    │  CertRequest    │  │
│  └──────┬───────┘    │  sign_csr() │    │  CRLState       │  │
│         │            │  gen_crl()  │    └─────────────────┘  │
│         │            └──────┬──────┘                          │
│         │                   │                                 │
│  ┌──────▼──────┐    ┌───────▼─────────────────────────────┐  │
│  │  Background  │    │           ca_root/ (Volume)          │  │
│  │  Worker      │    │  skysca_root.key  (RSA-4096)        │  │
│  │  DNS Verify  │    │  skysca_root.crt  (Self-signed CA)  │  │
│  └─────────────┘    │  latest.crl       (DER CRL)          │  │
│                      └─────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Technology Stack:**

| Layer | Technology |
|---|---|
| Framework | Django 4.2+ |
| Cryptographic Engine | Python `cryptography` (Hazmat) |
| Database | PostgreSQL (via `psycopg2-binary`, `dj_database_url`) |
| Background Tasks | `django-background-tasks` |
| DNS Resolution | `dnspython` |
| Static Files | WhiteNoise (compressed + cached) |
| WSGI Server | Gunicorn |
| Rate Limiting | `django-ratelimit` |

---

## 🔄 Certificate Lifecycle

Sky's CA models a complete, standards-compliant certificate lifecycle with the following status machine:

```
  ┌─────────┐    DNS-01 Verification     ┌────────┐
  │ pending │ ─────────────────────────▶ │ valid  │
  └─────────┘                            └───┬────┘
       │                                     │ Admin issues cert
       │ Verification fails                  ▼
       ▼                               ┌──────────┐    Revoke    ┌─────────┐
  ┌──────────┐                         │  issued  │ ───────────▶ │ revoked │
  │  failed  │                         └──────────┘              └─────────┘
  └──────────┘                               │
                                             │ Exceeds validity
                                             ▼
                                       ┌──────────┐
                                       │ expired  │
                                       └──────────┘
```

**Status Definitions:**

| Status | Meaning |
|---|---|
| `pending` | CSR submitted, awaiting DNS validation |
| `valid` | DNS TXT record verified; ready for issuance |
| `issued` | X.509 certificate signed and available for download |
| `revoked` | Certificate explicitly invalidated; serial in CRL |
| `expired` | Certificate validity period has elapsed |
| `failed` | DNS verification could not be completed |
| `rejected` | Manually rejected by an administrator |

---

## 🛣️ API / URL Reference

| Method | URL | Auth | Description |
|---|---|---|---|
| `GET` | `/` | Public | Homepage |
| `GET` | `/about/` | Public | About page |
| `GET` | `/signup/` | Public | User registration |
| `GET/POST` | `/login/` | Public | User authentication |
| `GET` | `/dashboard/` | User | Certificate management dashboard |
| `GET` | `/certificates/` | User | View all issued certificates |
| `POST` | `/generate-csr/` | User (rate-limited) | Submit CSR for a new certificate request |
| `GET` | `/certificate-generator/` | Public | Client-side key pair + CSR generator |
| `GET` | `/domain-verification/` | User | DNS verification status page |
| `POST` | `/verify-dns/<id>/` | User | Trigger DNS TXT lookup for a pending request |
| `POST` | `/issue-certificate/<id>/` | User | Sign and issue a validated certificate |
| `POST` | `/revoke-certificate/<id>/` | User | Revoke an issued certificate, regenerate CRL |
| `GET` | `/download-crl/` | Public | Download the current DER-encoded CRL |
| `GET` | `/installation-guides/` | Public | Certificate installation documentation |
| `GET` | `/key-generator/` | Public | Standalone key generation tool |
| `GET` | `/revocation/` | Public | Revocation process documentation |
| `GET` | `/support/` | Public | Support & contact page |

---

## 🗄️ Data Models

### `CertificateRequest`

The central model tracking the full lifecycle of every certificate.

| Field | Type | Description |
|---|---|---|
| `user` | `ForeignKey(User)` | Requesting user |
| `domain` | `CharField` | Extracted CN from the CSR subject |
| `csr` | `FileField` | Stored PEM-encoded CSR file |
| `certificate` | `FileField` | Issued PEM certificate (post-issuance) |
| `dns_token` | `CharField(64)` | UUID hex token for DNS-01 challenge |
| `status` | `CharField` | Lifecycle status (see above) |
| `verified` | `BooleanField` | True once DNS validation passes |
| `serial_number` | `CharField(128, unique)` | X.509 serial number for CRL tracking |
| `issued_at` | `DateTimeField` | Timestamp of issuance |
| `expires_at` | `DateTimeField` | Certificate expiry timestamp |
| `revoked` | `BooleanField` | Revocation boolean flag |
| `revoked_at` | `DateTimeField` | Timestamp of revocation |
| `revocation_reason` | `CharField` | RFC 5280 reason code string |
| `created_at` | `DateTimeField(auto_now_add)` | Request creation timestamp |
| `updated_at` | `DateTimeField(auto_now)` | Last modification timestamp |

**Helper methods:**
- `dns_record_name()` → Returns `_skysca.<domain>` (the DNS TXT record name to set)
- `dns_record_value()` → Returns the `dns_token` (the TXT value to set)

---

### `CRLState`

Singleton model maintaining the globally monotonic CRL number counter, a mandatory requirement of RFC 5280.

| Field | Type | Description |
|---|---|---|
| `current_crl_number` | `BigIntegerField` | Auto-incremented on each CRL generation |
| `last_generated` | `DateTimeField(auto_now)` | Timestamp of last CRL generation |

---

## 🔑 Cryptographic Engine (`ca_core.py`)

The heart of Sky's CA. All cryptographic operations are handled in `caCode/ca_core.py` using the Python `cryptography` library's low-level `hazmat` primitives.

### `setup_root_ca()`
- **Idempotent** — runs on every `sign_csr()` call but only generates files if they don't exist.
- Generates a **4096-bit RSA private key**.
- Self-signs a Root CA certificate valid for **10 years** with `BasicConstraints(ca=True)`.
- Persists `skysca_root.key` and `skysca_root.crt` to the `ca_root/` directory.

### `sign_csr(csr_pem_bytes)`
Signs a PEM-encoded CSR and returns `(cert_pem_bytes, serial_number_str)`.

The issued certificate includes the full X.509 v3 extension suite:

```
Extensions:
  BasicConstraints:            CA:FALSE (critical)
  SubjectKeyIdentifier:        <derived from CSR public key>
  AuthorityKeyIdentifier:      <derived from Root CA public key>
  KeyUsage:                    digitalSignature, keyEncipherment (critical)
  ExtendedKeyUsage:            serverAuth, clientAuth
  SubjectAlternativeName:      DNS:<domain from CSR CN>
  CRLDistributionPoints:       <CRL_DISTRIBUTION_URL from settings>
```

> **Security Note**: The domain is extracted directly from the CSR's `Subject.CN` field — the application never trusts a user-supplied domain name from form input.

### `generate_static_crl()`
- Called once after each revocation event.
- Queries all `CertificateRequest` objects with `status='revoked'` and a non-null `serial_number`.
- Builds a DER-encoded CRL with:
  - `CRLNumber` extension (monotonically increasing)
  - `AuthorityKeyIdentifier` extension
  - Per-entry `CRLReason` extension (using the stored RFC 5280 reason flag)
  - `lastUpdate` and `nextUpdate` fields (`7 days` ahead)
- Saves the artifact to `ca_root/latest.crl`.
- **Does not re-sign on every download** — the file is served statically until the next revocation event.

---

## 🔐 Security Design

### 1. Domain Validation (DNS-01)
Sky's CA will not issue a certificate for a domain unless the requester can prove ownership by publishing a specific TXT record. The required DNS record is:

```
Record Name:  _skysca.<your-domain>.com
Record Type:  TXT
Record Value: <unique uuid token from Sky's CA>
```

This is verified asynchronously by a background worker using `dnspython`, preventing the verification from blocking the web request.

### 2. Duplicate Issuance Prevention
The `issue_certificate` view explicitly returns `HTTP 400` if `cert.status == 'issued'`, preventing accidental or malicious re-issuance without a new CSR.

### 3. Static CRL Architecture
Unlike naive implementations that call `generate_crl()` on every `/download-crl/` request, Sky's CA generates the CRL **once** at revocation time and serves the static file. This design:
- Prevents attackers from triggering expensive RSA signing operations via DoS
- Eliminates race conditions on the monotonic CRL counter
- Ensures consistent CRL numbers (no gaps or duplicates)

### 4. Private Key Protection
- `ca_root/` is listed in `.gitignore` — it will never be committed to version control
- The key is stored unencrypted on the server's Persistent Volume (Railway), which is appropriate for a software CA; hardware HSM support can be added for production hardening
- For true enterprise environments: consider using an Intermediate CA for daily signing, keeping the Root CA completely air-gapped

### 5. Rate Limiting
The `/generate-csr/` endpoint is protected by `@ratelimit(key='ip', rate='5/m', block=True)` to prevent CSR flooding from a single IP.

### 6. CSRF & Cookie Security
Production settings (when `DJANGO_DEBUG=False`) enforce `CSRF_TRUSTED_ORIGINS` and the app respects Django's built-in CSRF middleware on all state-changing `POST` endpoints.

---

## 📋 Certificate Revocation List (CRL) Infrastructure

The CRL system is designed for correctness and performance in an enterprise context.

### Revocation Flow

```
User clicks "Revoke"
        │
        ▼
cert.status = 'revoked'
cert.revoked_at = now()
cert.revocation_reason = <RFC 5280 reason>
        │
        ▼
generate_static_crl()
        │
        ▼
Query all revoked certs with serial numbers
        │
        ▼
Build CRL (CRLNumber++, nextUpdate = now+7d)
        │
        ▼
Save  ca_root/latest.crl  (DER encoded)
```

### Distribution Flow

```
Client: GET /download-crl/
        │
        ▼
Serve  ca_root/latest.crl
Content-Type: application/pkix-crl
Cache-Control: public, max-age=3600
```

### Supported Revocation Reasons (RFC 5280)

| Reason | Code | Description |
|---|---|---|
| `unspecified` | 0 | No reason specified |
| `key_compromise` | 1 | Private key has been compromised |
| `ca_compromise` | 2 | CA's private key has been compromised |
| `affiliation_changed` | 3 | Subject's affiliation has changed |
| `superseded` | 4 | Certificate replaced by a new one |
| `cessation_of_operation` | 5 | Entity has ceased operation |
| `certificate_hold` | 6 | Temporarily on hold |
| `privilege_withdrawn` | 9 | Privileges have been withdrawn |
| `aa_compromise` | 10 | Attribute Authority compromised |

---

## 💻 Local Development

### Prerequisites
- Python 3.11+
- Git

### 1. Clone & Setup Environment

```bash
git clone https://github.com/your-username/skys-ca.git
cd skys-ca

python -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file (or set shell variables) — for local dev, defaults are fine:

```bash
# .env (never commit this)
DJANGO_SECRET_KEY=your-local-dev-secret-key-here
DJANGO_DEBUG=True
```

### 3. Apply Migrations & Create Superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

> On first run of the app, `ca_core.setup_root_ca()` will automatically generate a fresh 4096-bit Root CA key and self-signed certificate in `ca_root/`.

### 4. Run the Application

Sky's CA requires **two concurrent processes** — the web server and the background DNS verification worker.

**Terminal 1 — Web Server:**
```bash
python manage.py runserver
```

**Terminal 2 — Background Worker:**
```bash
python manage.py process_tasks
```

The application will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

### 5. Collect Static Files (for production testing)

```bash
python manage.py collectstatic --noinput
```

---

## 🚂 Railway Deployment

Sky's CA is purpose-built for 1-click deployment to [Railway.com](https://railway.com) via GitHub integration.

### Step 1 — Create a New Railway Project

1. Log in to [Railway.com](https://railway.com)
2. Click **New Project → Deploy from GitHub Repo**
3. Select your forked/cloned `skys-ca` repository

### Step 2 — Add PostgreSQL

1. Inside your Railway project, click **New Service → Database → PostgreSQL**
2. Railway will automatically create and inject the `DATABASE_URL` environment variable into your web service

### Step 3 — Set Environment Variables

In your Railway Web Service's **Variables** tab, add:

| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | A 50+ character random string ([generate one here](https://djecrety.ir/)) |
| `DJANGO_DEBUG` | `False` |

> `DATABASE_URL`, `RAILWAY_PUBLIC_DOMAIN`, and `PORT` are injected automatically by Railway.

### Step 4 — Attach a Persistent Volume (CRITICAL)

> ⚠️ **This step is mandatory.** Railway containers use an ephemeral filesystem — the `ca_root/` directory containing your Root CA private key will be destroyed on every deployment restart if a volume is not attached.

1. In your Railway Web Service, navigate to **Settings → Volumes**
2. Click **Add Volume**
3. Set the **Mount Path** to `/app/ca_root`
4. Deploy — your cryptographic identity is now permanently stored

### Step 5 — Run Migrations

Open the Railway **Shell** tab for your web service and run:

```bash
python manage.py migrate
python manage.py createsuperuser
```

### Step 6 — Deploy

Railway will detect the `Procfile` and boot the application using:

```
web: gunicorn skysca.wsgi --log-file -
```

> **Note on the Background Worker**: The `process_tasks` command (DNS verification worker) must be run as a separate Railway service pointing at the same repository. In the second service, override the Start Command to `python manage.py process_tasks`.

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Yes (prod) | Insecure fallback | Django's cryptographic signing key |
| `DJANGO_DEBUG` | No | `True` | Set to `False` in production |
| `DATABASE_URL` | Yes (prod) | SQLite fallback | Full database connection string |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated list of allowed host headers |
| `RAILWAY_PUBLIC_DOMAIN` | Auto (Railway) | — | Injected by Railway; used to set `CRL_DISTRIBUTION_URL` and `CSRF_TRUSTED_ORIGINS` automatically |

---

## 📂 Project Structure

```
skys-ca/
│
├── caCode/                          # Main Django application
│   ├── migrations/                  # Database migrations (13 total)
│   ├── static/
│   │   ├── css/main.css             # Glassmorphic dark theme
│   │   ├── img/logo.png             # Sky's CA branding
│   │   └── js/homepage.js           # Client-side animations
│   ├── templates/caCode/            # Jinja2-style Django templates
│   │   ├── base.html                # Global layout, nav, dark mode
│   │   ├── homepage.html            # Landing page
│   │   ├── dashboard.html           # Certificate lifecycle management
│   │   ├── certificate-generator.html # Web Crypto API key/CSR generation
│   │   ├── dns-verification.html    # DNS challenge status
│   │   ├── certificates.html        # Issued certificates list
│   │   └── ...                      # Support, about, login, signup, etc.
│   ├── admin.py                     # Django admin registrations
│   ├── apps.py                      # App configuration
│   ├── ca_core.py                   # PKI engine (Root CA, sign_csr, CRL)
│   ├── forms.py                     # SignUp, Login, CSR upload forms
│   ├── models.py                    # CertificateRequest, CRLState models
│   ├── urls.py                      # URL routing
│   └── views.py                     # Request handlers & business logic
│
├── ca_root/                         # ⚠️ GITIGNORED — PKI artifacts
│   ├── skysca_root.key              # 4096-bit RSA Root CA private key
│   ├── skysca_root.crt              # Self-signed Root CA certificate
│   └── latest.crl                  # Most recent DER-encoded CRL
│
├── skysca/                          # Django project configuration
│   ├── settings.py                  # All configuration (env-driven)
│   ├── urls.py                      # Root URL dispatcher
│   ├── wsgi.py                      # WSGI entry point (Gunicorn)
│   └── asgi.py                      # ASGI entry point (future async)
│
├── tests/                           # Integration & verification tests
│   ├── test_crl.py                  # CRL generation & parsing tests
│   ├── test_extensions.py           # X.509 extension verification
│   ├── test_issue.py                # Certificate issuance tests
│   └── test_verification.py         # DNS verification tests
│
├── .gitignore                       # Excludes ca_root/, media/, *.sqlite3
├── Procfile                         # gunicorn skysca.wsgi --log-file -
├── manage.py                        # Django management CLI
└── requirements.txt                 # Pinned production dependencies
```

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/intermediate-ca`)
3. Commit your changes following [Conventional Commits](https://www.conventionalcommits.org/)
4. Open a Pull Request with a clear description of the change

### Potential Enhancements
- [ ] **Intermediate CA**: Add a two-tier PKI hierarchy (Root → Intermediate → End-Entity)
- [ ] **OCSP Responder**: Implement Online Certificate Status Protocol as an alternative to CRL
- [ ] **ACME Protocol**: Implement the RFC 8555 ACME protocol for automated certificate issuance
- [ ] **Email Notifications**: Alert users on certificate expiry
- [ ] **HSM Integration**: Support PKCS#11 for hardware-backed key storage
- [ ] **Wildcard Certificates**: Support `*.domain.com` via DNS-01 challenge

---

## 📜 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for full details.

---

<div align="center">
  <sub>Built with ❤️ using Django &amp; Python <code>cryptography</code></sub>
</div>
