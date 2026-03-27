# Code4Boy Backend API

FastAPI backend for Code4Boy - handles user data sync, visitor analytics, and admin dashboard.

## Setup

### 1. Install Python dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env as needed (SQLite works by default for local dev)
```

### 3. Start the backend server
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will run at: http://localhost:8000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /healthz | Health check |
| POST | /api/user/sync | Sync user data |
| GET | /api/user/{uid} | Get user data |
| POST | /api/user/{uid}/update | Update user data |
| POST | /api/track/visit | Track page visit |
| POST | /api/track/download | Track file download |
| GET | /api/admin/stats | Admin analytics stats |
| GET | /api/admin/users | Admin user list |
| GET | /api/admin/visitors | Admin visitor list |
| GET | /api/admin/analytics/* | Various analytics endpoints |

## Database

- **Local dev**: SQLite (auto-created as `app.db`)
- **Production**: Set `DATABASE_URL` in `.env` for PostgreSQL (e.g., Neon)
