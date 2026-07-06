# LodgixHub

LodgixHub is a Django-based backend MVP for a short-term accommodation booking platform similar to Airbnb or Booking.com. The project covers hotels, hostels, and apartments through a unified listing model and is designed to be developed incrementally with explicit task approval before each implementation step.

## MVP Goal

The MVP target is to deliver a working backend by **July 22, 2026**. The system must provide authentication, role-based access, property listings, media upload, booking flows, dynamic price calculation, moderation, reviews, basic analytics, documentation, and deployment infrastructure.

This repository currently contains the initial Django project skeleton. The technical specification below is the agreed MVP scope and will be updated as implementation decisions are clarified.

## Development Agreement

Every task and every code or configuration change must be approved before implementation.

Before making changes, the assistant must explain:

- what task is being implemented;
- which files are expected to change;
- whether migrations will be created;
- whether dependencies will be added;
- which commands may need to be run.

If a requirement is unclear, ambiguous, or has multiple valid implementation options, the assistant must ask clarification questions before proceeding.

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

## Planned Backend Modules

The backend is expected to be split into focused Django apps:

- `config` - Django project configuration, settings, root URLs, ASGI, and WSGI entrypoints.
- `core` - shared base models, utilities, exceptions, validators, logging helpers.
- `users` - custom user model, authentication, permissions, groups, profiles.
- `listings` - listings, rooms, photos, moderation, search filters.
- `media` - listing and room photos, main photo selection, ordering, storage integration.
- `bookings` - booking lifecycle, cancellation reasons, confirmation, auto-cancellation.
- `pricing` - dynamic price calculation, deposits, price history.
- `reviews` - reviews, ratings, moderation.
- `analytics` - search history, view history, popularity aggregations.
- `notifications` - email notifications and signal handlers.

The existing `config` package remains the Django project configuration package. The planned `core` app is a separate reusable application for shared domain and infrastructure helpers. The exact structure may be adjusted during implementation after approval.

## Local Development Setup

The real `.env` file is local-only and must not be committed. Use `.env.example` as a safe template.

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

This project will use a dependency file such as `requirements.txt` after the dependency list is approved.

Expected command:

```bash
pip install -r requirements.txt
```

### 3. Create local environment file

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

### 4. Generate `SECRET_KEY`

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

macOS/Linux:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value into `SECRET_KEY` in the local `.env` file.

### 5. Configure database variables

For local MySQL development, fill these variables in `.env`:

```env
USE_MYSQL=True
MYSQL_NAME=db_name
MYSQL_USER=db_user_user
MYSQL_PASSWORD=change-me
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

The exact local MySQL database and user creation commands will be added after the database setup task is approved.

### 6. Run migrations

```bash
python manage.py migrate
```

### 7. Create an admin user

```bash
python manage.py createsuperuser
```

### 8. Run the development server

```bash
python manage.py runserver
```

## Documentation

- [Changelog](CHANGELOG.md)

## License

Copyright (c) 2026 devsmish. All rights reserved.

This software and its source code are proprietary and confidential.
Unauthorized copying, modification, distribution, or use of this file,
via any medium, is strictly prohibited.
