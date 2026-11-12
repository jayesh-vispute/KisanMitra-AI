@echo off
echo Starting KisanMitra AI...

cd /d "%~dp0"

if not exist backend\.env (
    echo Creating backend .env file from .env.example...
    copy backend\.env.example backend\.env
)

if not exist frontend\.env (
    echo Creating frontend .env file from .env.example...
    copy frontend\.env.example frontend\.env
)

echo [1/3] Setting up Backend...
cd backend
if not exist venv (
    echo Creating Python virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
echo Installing backend dependencies...
pip install -r requirements.txt

echo Starting Backend Server...
start "KisanMitra Backend" cmd /c "venv\Scripts\activate.bat && uvicorn main:app --reload --port 8008"

cd ..

echo [2/3] Setting up Frontend...
cd frontend
echo Installing frontend dependencies...
call npm install

echo Starting Frontend Server...
start "KisanMitra Frontend" cmd /c "npm run dev"

cd ..
echo [3/3] Setup complete!
echo Backend API is running on http://localhost:8008
echo Frontend Dashboard is running on http://localhost:5173
echo Keep the new windows open to keep the servers running.
pause
