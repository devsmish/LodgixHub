# Roadmap

This roadmap defines the planned implementation order for the LodgixHub backend MVP. Each stage must be approved before implementation starts.

## Stage 0 - Documentation and Planning

Status: in progress

- Maintain the technical specification in `README.md`.
- Maintain this roadmap.
- Maintain `CHANGELOG.md`.
- Clarify ambiguous requirements before implementation.

## Stage 1 - Project Foundation
refactor(#68): resolve analytics technical debt and optimize queries

- Fix thread-safety risk in AdminDashboardStatsView by avoiding class-level service instantiation.
- Fix N+1 query issue in dashboard zero-result searches using select_related.
- Clean up unit tests to reduce brittle monkey-patching of internals.
Status: planned

- Create the initial Django app structure.
- Configure Django REST Framework.
- Configure JWT authentication.
- Configure Swagger/OpenAPI documentation.
- Prepare environment-based settings.
- Prepare MySQL-compatible database settings.
- Add code quality tooling:
  - black;
  - isort;
  - pylint;
  - flake8.
- Decide and configure the custom user model before business migrations are created.
- Keep `config` as the Django project configuration package.
- Introduce `core` only for shared application logic, not as a replacement for `config`.

## Stage 2 - Users, Authentication, and Permissions

Status: planned

- Implement the custom user model.
- Implement registration and login endpoints.
- Implement JWT refresh flow.
- Implement route protection middleware.
- Implement custom token refresh middleware.
- Implement user capability flags, groups, or permission model.
- Support guest, authenticated user, landlord, moderator, and administrator access patterns.

## Stage 3 - Listings and Rooms

Status: planned

- Implement shared soft-delete base model.
- Implement `Listing`.
- Implement `Room`.
- Implement listing publication statuses.
- Implement landlord CRUD operations.
- Implement moderator status management.

## Stage 4 - Media and Content

Status: planned

- Implement photo upload for listings.
- Implement photo upload for rooms.
- Support multiple photos per object.
- Support main photo selection.
- Support photo display ordering.
- Support media soft delete.
- Use local media storage in development.
- Prepare S3-compatible storage integration for AWS deployment.

## Stage 5 - Search, Filtering, Sorting, and Basic Analytics

Status: planned

- Implement listing search.
- Implement listing filters.
- Implement listing sorting.
- Store search history.
- Store listing view history.
- Add SQL-based popularity statistics.

## Stage 6 - Bookings

Status: planned

- Implement booking creation.
- Implement booking detail and list endpoints.
- Implement booking confirmation.
- Implement booking cancellation.
- Implement `CancellationReason`.
- Require a cancellation reason for cancelled bookings.
- Prevent invalid or overlapping bookings.

## Stage 7 - Pricing and Deposits

Status: planned

- Implement dynamic price calculation.
- Implement early-booking discount logic.
- Implement late-booking discount logic.
- Implement deposit settings.
- Implement `PriceHistory` as append-only data.
- Prevent deletion of price history records.
- Prevent invalid same-day price changes.

## Stage 8 - Scheduled Commands

Status: planned

- Implement management command for automatic cancellation of unconfirmed bookings after 30 minutes.
- Apply business-hours rules to auto-cancellation.
- Implement management command for daily price setup.
- Configure cron execution inside the container.

## Stage 9 - Reviews and Ratings

Status: planned

- Implement review creation.
- Enforce one review per booking.
- Enforce the one-week review window after booking completion.
- Implement rating fields.
- Implement review moderation statuses.
- Implement moderator review status management.

## Stage 10 - Notifications, Logging, and Error Handling

Status: planned

- Implement synchronous email notifications.
- Trigger notifications from signals or views.
- Add structured logging.
- Add validation for core business rules.
- Add consistent exception handling.
- Add alert/notification signals where needed.

## Stage 11 - Demo Data and API Documentation

Status: planned

- Add Faker-based seed command.
- Fill demo users, listings, rooms, bookings, reviews, and price history.
- Finalize Swagger documentation.
- Verify main MVP flows through API documentation.

## Stage 12 - Docker and Deployment

Status: planned

- Add Dockerfile.
- Add Docker Compose.
- Add MySQL service for local development.
- Add cron support in the application container.
- Add Terraform infrastructure:
  - EC2;
  - RDS MySQL;
  - S3.

## Stage 13 - Stabilization and Quality (v1.1.x)

Status: in progress

Delivered:

- v1.1.0: black-box API end-to-end suite in `tests_e2e/` (pytest + Playwright `APIRequestContext`, Page Object Model) and core model unit tests in `core/tests_pt.py`.
- v1.1.1: repository-wide `isort`, `black` and `flake8` cleanup.
- v1.1.2: regression-tested bug fixes (Issue #170): booking validation returns `400` instead of `500`, public profile access accepts `pending` and `confirmed` bookings, `BaseModel.all_objects` supports bulk `restore()`, draft photo/room visibility and dynamic reference-data creation are covered by dedicated regression tests.

Planned (backlog under review):

- Docker-only development and test environment: MySQL init script granting the application user privileges on `test_*` databases, named volume instead of host paths.
- Split large `tests.py` modules into per-app `tests/` packages with shared factories.
- Run the full suite (unit and E2E) against MySQL 8 in Docker and fix engine-specific differences.
- Numeric correctness tests for pricing: total price, last-minute discounts, deposits.
- Search, filter, sorting and pagination tests for `GET /api/v1/listings/`.
- Management command and Celery task tests: `process_bookings`, `update_listing_current_price`.
- Configuration hygiene: JWT signing key length, refresh cookie flags, `manage.py check --deploy`.
- Synchronize the technical specification and API reference with the implemented behavior.
- GitHub Actions CI pipeline (moved up from Post-MVP): unit tests on every push, E2E tests on pull requests.

## Stage 14 - Post-MVP

Status: deferred

- RabbitMQ.
- Kafka.
- Redis.
- Node.js frontend.
- Real payment integration.
- Bonus and discount system beyond MVP dynamic pricing.
- 80% unit test coverage.
- Integration tests (black-box API E2E suite delivered in v1.1.0; further coverage is tracked in Stage 13).
- Playwright UI tests (API layer delivered in v1.1.0; the UI layer awaits the frontend).
- GitHub Actions CI/CD (the CI part is planned in Stage 13).
- Radon.
- Varnish.
- Nginx in front of frontend.
- Domain, SSL, and Cloudflare.
