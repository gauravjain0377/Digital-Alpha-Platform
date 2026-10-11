# ApexReconcile - Capital Call Bank Reconciliation

A multi-tenant bank reconciliation portal for General Partners (GPs) and Limited Partners (LPs). Automatically matches messy bank statement descriptions to capital call line items with full audit explanation and atomic approval workflows.

## Stack
- **Backend**: Django 6, Django REST Framework
- **Frontend**: React (Vite SPA)
- **Database**: PostgreSQL with Django migrations

---

## Quickstart

### 1. Backend Setup
```bash
cd backend
pip install -r ../requirements.txt
cp ../.env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```
Backend API will be running at `http://127.0.0.1:8000/`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173/` in your browser.

---

## Running Tests
Run all 8 assessment test suites with a single command from the root directory:
```bash
python backend/manage.py test reconciliation
```

---

## Documentation
For full architectural details, API endpoints, data models, and trade-offs, see [ASSESSMENT_NOTES.md](ASSESSMENT_NOTES.md).
