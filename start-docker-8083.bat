@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "MYSQL_ROOT_PASSWORD=change-me"
set "APP_JWT_SECRET=dev-only-jwt-secret-change-me-1234567890"
set "FRONTEND_HOST_PORT=8083"
set "BACKEND_HOST_PORT=18083"
set "MYSQL_HOST_PORT=13307"
set "APP_CORS_ALLOWED_ORIGINS=http://localhost:8083,http://127.0.0.1:8083"

echo Starting RealTimeCollabDoc on http://127.0.0.1:8083 ...
docker compose up --build -d
if errorlevel 1 goto :error

echo.
echo Frontend: http://127.0.0.1:8083
echo Backend:  http://127.0.0.1:18083/api
echo MySQL:    127.0.0.1:13307
echo.
echo Demo account: admin / password123
goto :end

:error
echo.
echo Docker startup failed.
exit /b 1

:end
endlocal
