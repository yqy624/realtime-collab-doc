#!/bin/bash
set -e

MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-change-me}"
APP_JWT_SECRET="${APP_JWT_SECRET:-dev-only-jwt-secret-change-me-1234567890}"
BACKEND_HOST_PORT="${BACKEND_HOST_PORT:-8082}"
FRONTEND_HOST_PORT="${FRONTEND_HOST_PORT:-3000}"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Using Docker Compose to start MySQL, backend, and frontend..."
  MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  APP_JWT_SECRET="$APP_JWT_SECRET" \
  BACKEND_HOST_PORT="$BACKEND_HOST_PORT" \
  FRONTEND_HOST_PORT="$FRONTEND_HOST_PORT" \
  docker compose up --build
  exit 0
fi

echo "Docker Compose was not detected. Falling back to local development mode."
echo "Make sure MySQL 8 is running and the database collab_doc exists."

# Start Python backend
(
  cd python-backend
  pip install -r requirements.txt -q
  python run.py
) &

# Start frontend
(
  cd frontend
  npm install
  export VITE_PROXY_TARGET="http://127.0.0.1:${BACKEND_HOST_PORT}"
  npm run dev -- --host 127.0.0.1 --port "$FRONTEND_HOST_PORT"
) &

wait
