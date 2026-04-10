@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo ======================================
echo Placement Portal - Run Everything
echo ======================================
echo.

where conda >nul 2>nul
if errorlevel 1 (
	echo ERROR: conda command not found in PATH.
	echo Open Anaconda Prompt or add conda to PATH and retry.
	pause
	exit /b 1
)

call conda env list | findstr /R /C:"^placement_portal[ ]" >nul
if errorlevel 1 (
	echo ERROR: Conda env placement_portal not found.
	echo Create it first, then install backend requirements.
	pause
	exit /b 1
)

echo Checking backend dependencies in placement_portal...
call conda run -n placement_portal python -c "import flask, flask_sqlalchemy, flask_migrate, flask_jwt_extended, flask_cors, flask_caching, dotenv, redis, celery" >nul 2>nul
if errorlevel 1 (
	echo WARNING: Some backend dependencies are missing.
	echo Run: conda run -n placement_portal pip install -r backend\requirements.txt
	pause
	exit /b 1
)

echo Starting Backend API on port 5000...
start "Backend API" cmd /k "cd /d ""%ROOT%backend"" & echo [Backend] Starting Flask API... & call conda run --live-stream -n placement_portal python -m flask --app run.py run --debug --port 5000"

echo Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d ""%ROOT%backend"" & echo [Worker] Starting Celery worker... & call conda run --live-stream -n placement_portal celery -A celery_worker.celery worker --loglevel=info --pool=solo"

echo Starting Celery Beat...
start "Celery Beat" cmd /k "cd /d ""%ROOT%backend"" & echo [Beat] Starting Celery beat... & call conda run --live-stream -n placement_portal celery -A celery_worker.celery beat --loglevel=info"

echo Starting Frontend (Vite)...
start "Frontend" cmd /k "cd /d ""%ROOT%frontend"" & npm install & npm run dev"

echo.
echo All processes were launched in separate windows.
echo Frontend URL: http://localhost:5174
echo Backend URL:  http://127.0.0.1:5000/api
echo.
echo One-time setup if DB was deleted:
echo conda run -n placement_portal python -m flask --app backend/run.py init-db
echo conda run -n placement_portal python -m flask --app backend/run.py seed-demo
echo.
pause
