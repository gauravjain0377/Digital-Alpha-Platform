# Assessment Notes - ApexReconcile

## App Name
**ApexReconcile** (Bank Reconciliation for Capital Calls)

---

## Fresh Clone Setup

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL running locally

### 2. Backend Setup
```bash
cd backend
pip install -r ../requirements.txt

# Create .env from template
cp ../.env.example .env

# Run database migrations
python manage.py migrate

# Seed demo data (idempotent)
python manage.py seed_demo

# Start backend server (runs on http://127.0.0.1:8000)
python manage.py runserver
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# App is available at http://localhost:5173
```

---

## Environment Variables (`.env.example`)

```env
SECRET_KEY=django-insecure-alpha-recon-dev-key
DEBUG=True
ALLOWED_HOSTS=*

DB_NAME=digital_alpha
DB_USER=postgres
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5433

CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## Single Command to Run Tests

From repository root:
```bash
python backend/manage.py test reconciliation
```
(Or from `backend/`: `python manage.py test`)

---

## Data Model

- **Organization**: Multi-tenant GP firm (`name`, `slug`).
- **InvestorEntity**: LP legal entity tied to an organization (`name`, `organization`).
- **CapitalCall**: Notice issued by GP (`call_number`, `call_date`, `due_date`, `organization`).
- **LineItem**: Expected payment per LP (`reference`, `amount_called`, `amount_funded`, `status`). Computed `amount_remaining`.
- **BankTransaction**: Imported bank entry (`date`, `description`, `amount` as `Decimal`, `type`, `bank_reference` unique per org, `status`, `review_reason`).
- **TransactionMatch**: Link between a transaction and a line item (`status`, `reason`).

---

## API Endpoints

All endpoints except `/api/organizations/` require the `X-Organization` header.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/organizations/` | List all organizations for the switcher |
| `POST` | `/api/import/` | Upload CSV bank statement; returns import summary & row errors |
| `GET` | `/api/transactions/` | List transactions with matches and reasons (newest first) |
| `GET` | `/api/line-items/` | List line items with called, funded, remaining, and status |
| `POST` | `/api/matches/<id>/approve/` | Atomically approve match, lock row, update line item, prevent double-funding (returns `409` on conflict) |
| `POST` | `/api/matches/<id>/reject/` | Reject match; reverts transaction to `needs_review` if no proposals remain |
| `POST` | `/api/transactions/<id>/ignore/` | Ignore transaction and reject its proposals (`409` if reconciled) |

---

## Assumptions & Trade-offs

1. **Precision & Money Handling**: `Decimal` is used across all models, parsers, and calculations to eliminate float rounding errors.
2. **Tenant Isolation**: Handled via `X-Organization` header. Missing header yields `400`; records belonging to other tenants return `404` (not `403`).
3. **Reference Uniqueness**: Bank references are enforced unique per organization (`unique_together = ('organization', 'bank_reference')`).
4. **Name Normalization**: Suffixes `LLC`, `LP`, `LTD`, and `INC` are stripped while `TRUST` is preserved. Word boundary matching prevents partial substring false-positives.
5. **Concurrency & Double-Funding**: The approve action utilizes `select_for_update()` inside an atomic transaction to guarantee no race condition can double-fund a line item.

---

## Next Steps
- Add background worker processing (Celery) for multi-gigabyte statement uploads.
- Add audit logging for approval and rejection history.
- Add export functionality for reconciliation reports.

---

## Integrity Line
I confirm that this submission is my own original work and adheres to all technical assessment guidelines.
