@echo off
echo ========================================
echo    RAGify - Starting Local Demo Server
echo ========================================
echo.
echo [1/2] Starting FastAPI Backend on port 9999...
start cmd /k "cd backend && python -m uvicorn main:app --reload --port 9999"

echo Waiting 5 seconds for backend to initialize...
timeout /t 5 /nobreak

echo.
echo [2/2] Starting Localtunnel with FIXED subdomain...
echo Your backend will be available at: https://ragify-backend.loca.lt
echo.
echo IMPORTANT: When Localtunnel asks for a password, go to:
echo   https://loca.lt/mytunnelpassword
echo   Copy the password and paste it in the tunnel window.
echo.
start cmd /k "npx localtunnel --port 9999 --subdomain ragify-backend"

echo.
echo ========================================
echo  Frontend: https://ragify.vercel.app
echo  Backend:  https://ragify-backend.loca.lt
echo ========================================
echo Share the Vercel link with anyone!
pause
