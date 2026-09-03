#Django Task Tracker

A simple task management API built with Django.

## Features

- User registration and login
- JWT authentication
- Create, view, update, and delete tasks
- Task ownership — users can access only their own tasks
- PostgreSQL database
- Application logging
- Dockerized application
- Gunicorn application server
- nginx reverse proxy

## Tech Stack

- Python
- Django
- PostgreSQL
- JWT
- Gunicorn
- nginx
- Docker

## Architecture

```text
Client
  ↓
nginx
  ↓
Gunicorn
  ↓
Django
  ↓
PostgreSQL
```

## Configuration

Environment variables are configured in:

```text
config/.env
```

An example configuration is available in:

```text
config/.env.example
```

## API

### Authentication

```text
POST /auth/register
POST /auth/login
```

### Tasks

```text
GET    /tasks/
POST   /tasks/
GET    /tasks/<id>/
PUT    /tasks/<id>/
DELETE /tasks/<id>/
```

Task endpoints require JWT authentication.

## How to run the Project

Create the environment file from the example:

```bash
cp config/.env.example config/.env
```

Set the required values in `config/.env`.

Build and start the application:

```bash
docker compose up -d --build
```

The API will be available at:

```text
http://localhost:8000
```

Database migrations are applied automatically on startup.

## API Endpoints

### Authentication

```text
POST /auth/register
POST /auth/login
```

### Tasks

```text
GET    /tasks/
POST   /tasks/
GET    /tasks/<id>/
PUT    /tasks/<id>/
DELETE /tasks/<id>/
```

## Tests

The project includes automated tests for authentication, task management, permissions, and logging.

~Task endpoints require JWT authentication.~
