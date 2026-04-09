# Placement Portal Application (V2)

Tech stack used strictly as requested:
- Flask API
- Vue.js UI
- Bootstrap styling
- SQLite database
- Redis caching
- Celery + Redis batch jobs

## Project structure
- backend/: Flask API, SQLite models, Redis cache, Celery tasks
- frontend/: Vue + Bootstrap UI

## Backend setup
Run from `backend/`:
1. Create virtual env (or use conda env) and activate it.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill SMTP/secret values.
4. Initialize DB and auto-create admin:
   `python -m flask --app run.py init-db`
5. Optional: seed demo data for fast walkthrough:
   `python -m flask --app run.py seed-demo`
6. Start API:
   `python -m flask --app run.py run --debug --port 5000`

## Celery setup
Run from backend folder:
- Worker: `celery -A celery_worker.celery worker --loglevel=info --pool=solo`
- Beat: `celery -A celery_worker.celery beat --loglevel=info`

## Frontend setup
Run from frontend folder:
1. npm install
2. npm run dev

Default API base URL is `http://127.0.0.1:5000/api`.

## Implemented
- Unified role-based auth model (Admin, Company, Student)
- Programmatic DB init command with pre-existing Admin creation
- Admin APIs: approvals, searches, status controls, drive listing, applications listing, pagination support
- Company APIs: drive creation, applicant management, status updates, interview scheduling
- Student APIs: approved drives, eligibility checks, apply, profile updates, history, async export trigger
- Celery tasks: daily reminders, monthly report, CSV export (task status lifecycle improved)
- Redis-backed Flask caching on admin dashboard and mutation invalidation hooks
- Vue UIs: role login/register plus Admin/Company/Student workflow screens

## In Progress / Remaining
- End-to-end test pass for all role flows with real sample data
- Runtime validation of Redis + Celery worker + Celery beat in local demo session
- Optional UX polish (toast notifications, loading states refinement)

## Quick Demo Flow
1. Run `python -m flask --app run.py seed-demo` from backend folder.
2. Login as Admin (`admin@institute.local` / `admin123`).
3. Verify seeded company/drive/application in Admin dashboard and stats.
4. Login as Company (`company.demo@corp.local` / `company123`) and shortlist/select the student.
5. Login as Student (`student.demo@college.local` / `student123`) and check status/history.
6. From Student dashboard, trigger CSV export and check task status.

## Smoke Test
Run from backend folder to verify core flow quickly:
- `python smoke_test.py`

It validates:
- Admin/company/student login
- Company drive creation
- Admin drive approval
- Student apply to approved drive
- Duplicate apply prevention
- Company shortlist action

## Notes
- Admin registration is intentionally not provided.
- Company login is blocked until admin approval.
- Duplicate student applications to the same drive are prevented at API + DB constraint level.
