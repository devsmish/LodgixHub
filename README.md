# LodgixHub

LodgixHub is a Django-based backend MVP for a short-term accommodation booking platform similar to Airbnb or Booking.com. 
The project covers hotels, hostels, and apartments through a unified listing model and is designed to be developed 
incrementally with explicit task approval before each implementation step.

## MVP Goal

The MVP target is to deliver a working backend by **July 22, 2026**. The system must provide authentication, role-based 
access, property listings, media upload, booking flows, dynamic price calculation, moderation, reviews, basic analytics, 
documentation, and deployment infrastructure.

This repository contains the foundational backend setup and the initial Django app structure for the MVP (Version 0.2.0).

## Development Agreement

Every task and every code or configuration change must be approved before implementation.

Before making changes, the assistant must explain:
- what task is being implemented;
- which files are expected to change;
- whether migrations will be created;
- whether dependencies will be added;
- which commands may need to be run.

If a requirement is unclear, ambiguous, or has multiple valid implementation options, the assistant must ask 
clarification questions before proceeding.

## Functional Scope

### Authentication and Authorization
- JWT authentication.
- Route protection middleware.
- Custom middleware for token refresh behavior.
- User access model with multiple capabilities instead of a single exclusive role.
- Supported access levels and permissions:
  - guest;
  - authenticated user;
  - landlord;
  - moderator;
  - administrator.
- A user may act as both tenant and landlord through flags, groups, or permissions.

### Listings
- Unified `Listing` model for:
  - apartment;
  - hotel;
  - hostel.
- Listing type is represented by a `type` field.
- Related `Room` model for hotel and hostel inventory.
- Listing publication statuses:
  - draft;
  - published;
  - hidden;
  - rejected.
- Listing status can be edited by a moderator.
- Search, filtering, and sorting over listings.
- Soft delete through a shared base model.

### Media and Content
- Photo upload for listings.
- Photo upload for rooms.
- Multiple photos per listing or room.
- Main photo selection.
- Photo display ordering.
- Soft delete for media records.
- Local media storage for development.
- S3-ready media storage for AWS deployment.

### Bookings
- Booking creation.
- Booking viewing.
- Booking cancellation.
- Booking confirmation.
- Cancellation requires a reason selected from `CancellationReason`.
- Unconfirmed bookings are automatically cancelled after 30 minutes, taking business hours into account.

### Pricing
- Dynamic price calculation on demand.
- Early-booking and late-booking discounts.
- No real payment processing in the MVP.
- Payment integration remains a placeholder outside the MVP.
- `PriceHistory` table:
  - append-only;
  - updated by a daily cron-driven management command;
  - cannot be deleted;
  - cannot change the price for "today to today".
- Deposit configuration:
  - deposit required or not required;
  - percentage value;
  - refundable or non-refundable.

### Reviews and Ratings
- Reviews and ratings.
- One review per completed booking.
- Review window is limited to one week after booking completion.
- Review statuses:
  - draft;
  - published;
  - hidden;
  - rejected.
- Review status can be edited by a moderator.

### Analytics
- Search history.
- Listing view history.
- Basic listing popularity statistics using regular SQL aggregations.
- Kafka is intentionally excluded from the MVP.

### Notifications and Operations
- Synchronous email notifications.
- Emails are sent directly from signals or views.
- Exception handling with `try`/`except` where appropriate.
- Logging.
- Validation.
- Signals for alerts and notifications.
- Automatic booking cancellation through a system cron inside the container.
- Daily price setup through a system cron inside the container.

### Test Data
- Faker-based database seeding for development and demonstration data.

### API Documentation
- Swagger/OpenAPI documentation for the backend API.

### Code Quality
- Black.
- isort.
- pylint.
- flake8.
- PEP 8 oriented formatting and linting.

### Infrastructure
- Docker Compose for local/containerized execution.
- MySQL for local development.
- AWS deployment through Terraform:
  - EC2 for the application;
  - RDS MySQL for the database;
  - S3 for listing photos.

## Out of MVP Scope

The following items are intentionally postponed for post-defense self-development:
- RabbitMQ for email queues.
- Kafka for analytics or search logging.
- Redis for caching or as a broker.
- Node.js frontend and backend integration.
- Real payment processing.
- Discount and bonus system beyond on-demand price recalculation.
- 80% unit test coverage.
- Integration tests.
- Playwright UI tests.
- GitHub Actions CI/CD.
- Radon.
- Varnish.
- Nginx in front of the frontend.
- Domain setup.
- SSL.
- Cloudflare.

### Backend Implementation Status
All core application modules planned for the platform MVP have been successfully migrated to a stabilized 3-Tier Layered 
Architecture (`Controller → Service → Repository`) and are fully connected via API version `v1` routes as of 
release `v0.6.0`.

## Planned Backend Modules

The backend is split into focused Django apps:
- `config` - Django project configuration, settings, root URLs, ASGI, and WSGI entrypoints.
- `core` - shared base models, utilities, exceptions, validators, logging helpers.
- `apps/users` - custom user model, authentication, permissions, gender records, choices layout.
- `apps/security` - token rotation middleware layer, authorization access rules, and custom DRF permission authenticators.
- `apps/listings` - listings, rooms, photos, moderation, search filters.
- `apps/content` - listing and room photos, main photo selection, ordering, storage integration.
- `apps/bookings` - booking lifecycle, cancellation reasons, confirmation, auto-cancellation.
- `apps/pricing` - dynamic price calculation, deposits, price history.
- `apps/reviews` - reviews, ratings, moderation.
- `apps/analytics` - search history, view history, popularity aggregations.
- `apps/notifications` - email notifications and signal handlers.

The existing `config` package remains the Django project configuration package. The `core` app is a separate reusable 
application for shared domain and infrastructure helpers.

### Standardized Application Directory Layout

To maintain strict separation of concerns, predictable developer experience, and micro-component modularity, every 
application within the `apps/` directory is standardized to use the following package layout (enforced in 
Milestone 0.3.0):

```text
app_name/
├── migrations/     # Database ledger version files
├── choices/        # Enum-like classes for field states and type definitions
├── constants/      # App-specific business logic limits, timeouts, and thresholds
├── models/         # Multi-file domain entity definitions (exposed via __init__.py)
├── dto/            # Data Transfer Objects, request/response schemas, and serializers
├── errors/         # Domain-specific custom exception classes and error codes
├── filters/        # Advanced query search, filter, and sorting logic
├── paginations/    # Custom list response pagination definitions
├── repositories/   # Isolated database access layer (QuerySets, complex ORM logic)
├── services/       # Pure business logic orchestration layer
├── controller/     # Thin API request/response handling layer (views/endpoints)
├── admin.py        # Django Admin site panel registration
├── apps.py         # App config mapping
└── urls.py         # Module routing layout

## Local Development Setup

The real `.env` file is local-only and must not be committed. Use `.env.example` as a safe template.

### 1. Create and Activate a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

This project uses `requirements.txt` for managing dependencies. Ensure your virtual environment is active, then run:
```bash
pip install -r requirements.txt
```

### 3. Create Local Environment File

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

### 4. Generate SECRET_KEY

Generate a secure random key for your local environment:

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

**macOS / Linux:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value into `SECRET_KEY` in the local `.env` file.

### 5. Configure Database Variables

For local MySQL development, fill these variables in `.env`:
```env
USE_MYSQL=True
MYSQL_NAME=db_name
MYSQL_USER=db_user_user
MYSQL_PASSWORD=change-me
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```
*Note: The exact local MySQL database and user creation commands will be added after the database setup task is approved.*

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create an Admin User

```bash
python manage.py createsuperuser
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

### 9. Containerized Development Setup (Docker)

As of release `v0.5.0`, the application is fully containerized for local development to ensure environment consistency and eliminate host machine dependency mismatches.

#### Prerequisites
- Docker and Docker Compose installed on your host machine.
- Ports `8000` (application) and `3307` (MySQL external map) free from conflicts.

#### Environment Configuration
Create a dedicated `.env.docker` file based on `.env.example`:
* Change `MYSQL_HOST` to `db` (the service orchestrator name).
* Configure `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` to automate admin creation.

#### Execution Commands

* **Build and run the services in the foreground:**
  ```bash
  docker compose up --build
  
* **Run services in the background (detached mode):**
  ```bash
  docker compose up -d
 
* **Stop containers while preserving state (volume data):**
  ```bash
  docker compose down
  
* **Completely wipe container volumes and reset the database environment:**
  ```bash
  docker compose down -v
  
Once operational, the Django application will serve traffic at http://127.0.0.1:8000/. 
External database clients can attach to the isolated MySQL engine via 127.0.0.1:3310.

## Documentation
- [Changelog](CHANGELOG.md)

## License
Copyright (c) 2026 devsmish. All rights reserved.

This software and its source code are proprietary and confidential.
Unauthorized copying, modification, distribution, or use of this file,
via any medium, is strictly prohibited.
