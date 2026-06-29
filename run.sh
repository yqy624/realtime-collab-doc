#!/bin/bash
set -e

MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-change-me}"
APP_JWT_SECRET="${APP_JWT_SECRET:-dev-only-jwt-secret-change-me-1234567890}"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Using Docker Compose to start MySQL, backend, and frontend..."
  MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" APP_JWT_SECRET="$APP_JWT_SECRET" docker compose up --build
  exit 0
fi

echo "Docker Compose was not detected. Falling back to local development mode."
echo "Make sure MySQL 8 is running and the database collab_doc exists."

(
  cd backend
  export SPRING_DATASOURCE_PASSWORD="$MYSQL_ROOT_PASSWORD"
  export APP_JWT_SECRET="$APP_JWT_SECRET"
  mvn spring-boot:run
) &

(
  cd frontend
  npm install
  npm run dev -- --host 127.0.0.1 --port 3000
) &

wait
