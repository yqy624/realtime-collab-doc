# RealTimeCollabDoc

RealTimeCollabDoc is a real-time collaborative document MVP built with Spring Boot 3, Vue 3, WebSocket/STOMP, and MySQL.

## Features

- User registration and login with JWT authentication
- Document CRUD operations
- Real-time collaborative plain text editing
- In-document chat
- Online user presence
- Snapshot and revision support for collaborative sessions

## Tech Stack

- Backend: Spring Boot 3.1, Spring Security, Spring WebSocket, Spring Data JPA
- Frontend: Vue 3, TypeScript, Vite, Pinia, Element Plus
- Database: MySQL 8
- Real-time messaging: WebSocket + STOMP

## Project Structure

```text
collab-doc-project/
├── backend/
├── frontend/
├── docker-compose.yml
├── README.md
├── LICENSE
└── run.sh
```

## Local Development

### Prerequisites

- Java 17
- Maven 3.9+
- Node.js 20+
- MySQL 8

### Database Configuration

Create a MySQL database named `collab_doc`, then provide credentials with environment variables.

Windows PowerShell:

```powershell
$env:SPRING_DATASOURCE_USERNAME="root"
$env:SPRING_DATASOURCE_PASSWORD="your-mysql-password"
$env:APP_JWT_SECRET="replace-with-a-long-random-secret"
```

Bash:

```bash
export SPRING_DATASOURCE_USERNAME=root
export SPRING_DATASOURCE_PASSWORD=your-mysql-password
export APP_JWT_SECRET=replace-with-a-long-random-secret
```

### Start the Backend

```bash
cd backend
mvn spring-boot:run
```

The backend runs at `http://127.0.0.1:8080/api`.

### Start the Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

The frontend runs at `http://127.0.0.1:3000`.

## Docker Compose

Use environment variables instead of hard-coded secrets before starting:

Windows PowerShell:

```powershell
$env:MYSQL_ROOT_PASSWORD="your-mysql-password"
$env:APP_JWT_SECRET="replace-with-a-long-random-secret"
./run.sh
```

Bash:

```bash
export MYSQL_ROOT_PASSWORD=your-mysql-password
export APP_JWT_SECRET=replace-with-a-long-random-secret
./run.sh
```

If Docker Compose is available, `run.sh` starts MySQL, the backend, and the frontend together. Otherwise it falls back to local development mode.

## Test Accounts

The app seeds a few demo accounts during initialization for local testing:

- `admin`
- `user1`
- `user2`

Default demo password: `password123`

## Build Verification

The project can be verified with:

```bash
cd backend
mvn -q -DskipTests package

cd ../frontend
npm run build
```

## Notes

- The editor uses `contenteditable` plus a basic OT-style synchronization strategy for MVP use.
- Do not commit real database passwords, production JWT secrets, or personal environment files.
