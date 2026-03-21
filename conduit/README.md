# Conduit – HIPAA-Compliant Referral Transfer Agent

Conduit automates the transfer of patient referral data from ModMed (FHIR R4) to
downstream EHR systems, portals, or FHIR servers. All transfers are audit-logged
with de-identified events per HIPAA §164.312(b).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Conduit Backend (FastAPI)                │
│                                                                  │
│  ┌──────────────┐   ┌─────────────────┐   ┌─────────────────┐  │
│  │  FHIR Client │──▶│ Transform Engine│──▶│  Destination    │  │
│  │  (ModMed R4) │   │  (JSON Mappings)│   │  Connectors     │  │
│  │  OAuth 2.0   │   │                 │   │  api /          │  │
│  └──────────────┘   └─────────────────┘   │  fhir_write /   │  │
│                                            │  browser        │  │
│  ┌──────────────────────────────────────┐  └─────────────────┘  │
│  │  Audit Logger (PostgreSQL)           │                        │
│  │  De-identified HMAC patient tokens  │                        │
│  └──────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  React Dashboard    │
                   │  Transfer Status    │
                   │  Audit Log View     │
                   └─────────────────────┘
```

## Quick Start

```bash
# 1. Clone and set up environment
cp backend/.env.example backend/.env
# Edit backend/.env with your ModMed credentials

# 2. Start all services
docker compose up

# 3. Access
#   API docs:     http://localhost:8000/docs
#   Dashboard:    http://localhost:3000
#   Health check: http://localhost:8000/api/v1/health

# 4. Optional: start local FHIR server (HAPI) for end-to-end testing
docker compose --profile fhir up
```

## Project Structure

```
conduit/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── db.py                # Async SQLAlchemy engine
│   │   ├── models/              # ORM: Transfer, AuditLog
│   │   ├── routers/             # health, transfers, patients, audit
│   │   ├── fhir/                # FHIR R4 client + OAuth 2.0 auth
│   │   ├── transform/           # Transformation engine + JSON mappings
│   │   │   └── mappings/        # Per-resource mapping files
│   │   ├── audit/               # HIPAA audit logger
│   │   ├── connectors/          # API / FHIR write / Browser connectors
│   │   └── services/            # Transfer orchestration service
│   └── tests/                   # pytest test suite
├── frontend/
│   └── src/
│       ├── pages/               # TransfersPage, TransferDetailPage, AuditPage
│       ├── components/          # TransferTable, AuditTable, StatusBadge
│       └── api/                 # Typed axios client
├── test_data/
│   └── fhir/                    # Synthetic FHIR R4 test resources
└── docker-compose.yml
```

## FHIR Resources Supported

| Resource | Search Param | Required |
|---|---|---|
| Patient | (by ID) | ✅ |
| Coverage | patient | ✅ |
| Condition | patient | ✅ |
| Procedure | patient | ➖ |
| ServiceRequest | patient | ✅ |
| Practitioner | (by reference) | ➖ |
| DocumentReference | patient | ➖ |
| AllergyIntolerance | patient | ✅ |
| MedicationRequest | patient | ✅ |

## Destination Connectors

| Type | Config Keys | Notes |
|---|---|---|
| `api` | `url`, `method`, `headers`, `batch_size` | REST POST/PUT |
| `fhir_write` | `base_url`, `token_url`, `client_id`, `client_secret` | FHIR transaction Bundle |
| `browser` | `login_url`, `form_selectors`, `submit_selector` | Playwright (optional) |

## Custom Mappings

Add per-destination mapping overrides:
```
backend/app/transform/mappings/
├── Patient.json           ← generic
├── Condition.json
└── my-ehr/                ← destination-specific (takes precedence)
    └── Patient.json
```

## Running Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

## HIPAA Controls

- **§164.312(b) Audit Controls** – Every FHIR fetch, transform, and delivery is logged
- **De-identification** – Patient IDs are replaced with HMAC-SHA256 tokens before storage
- **No PHI at rest** – Raw resource payloads are never persisted to the database
- **Retention** – Audit logs retained for 7 years (configurable via `AUDIT_RETENTION_DAYS`)
- **TLS** – All external connections use HTTPS (enforced by httpx `verify=True` default)

## AWS Deployment Notes

- Use **AWS RDS Aurora PostgreSQL Serverless v2** for the database
- Store secrets in **AWS Secrets Manager** (map to env vars via ECS task definition)
- Use **AWS KMS** to replace `ENCRYPTION_KEY` with a KMS-backed HMAC key
- Run on **AWS ECS Fargate** behind an **Application Load Balancer** with WAF
- Enable **CloudWatch Logs** and **CloudTrail** for additional audit coverage
