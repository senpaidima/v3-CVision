# CVision v3

AI Employee Search + Lastenheft Analyzer

## Structure

```
v3-CVision/
├── backend/    # FastAPI + Python 3.11
├── frontend/   # React 18 + Vite 6 + TypeScript
└── .github/    # CI/CD workflows
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Testing

```bash
cd backend && python -m pytest tests/ -v
cd frontend && npx vitest run
```
