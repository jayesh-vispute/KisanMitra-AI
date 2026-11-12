#!/bin/bash

echo "Starting KisanMitra AI..."

# Change to the directory of the script
cd "$(dirname "$0")"

if [ ! -f backend/.env ]; then
    echo "Creating backend .env file from .env.example..."
    cp backend/.env.example backend/.env
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend .env file from .env.example..."
    cp frontend/.env.example frontend/.env
fi

echo "[1/3] Setting up Backend..."
cd backend
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing backend dependencies..."
pip install -r requirements.txt

echo "Starting Backend Server in the background..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

cd ..

echo "[2/3] Setting up Frontend..."
cd frontend
echo "Installing frontend dependencies..."
npm install

echo "Starting Frontend Server in the background..."
npm run dev &
FRONTEND_PID=$!

cd ..
echo "[3/3] Setup complete!"
echo "Backend API is running on http://localhost:8000"
echo "Frontend Dashboard is running on http://localhost:5173"
echo "Press Ctrl+C to stop both servers."

# Wait for background processes to finish (or when user presses Ctrl+C)
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
