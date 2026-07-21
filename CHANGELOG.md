# Changelog

All notable changes to LodgixHub will be documented in this file.

The format follows a simple chronological structure.

## [1.0.0] - 2026-07-21

### Fixed
- **Django Admin Interface:** Fixed plain-text password rendering and form validation failures during user creation in `CustomUserAdmin` by correctly referencing `password1` and `password2` form fields instead of the raw model field `password`.

### Refactored
- **OpenAPI / Swagger Schema Introspection (drf-spectacular):**
  - **UUID Path Parameter Preservation:** Configured static class-level `queryset` attributes on `BookingViewSet` and `ReviewViewSet`, preventing schema introspection fallback from `uuid` to `string`.
  - **Complete Schema Introspection Coverage:** Added explicit `@extend_schema` decorators and DTO response serializers across `apps.security`, `apps.users`, `apps.listings`, and `apps.admin` controllers (reducing schema errors from 28 to 0).
  - **Custom JWT Swagger Integration:** Registered `OpenApiAuthenticationExtension` for `CustomJWTAuthentication` in `apps.security.schema` to enable interactive "Authorize" functionality in Swagger UI.
  - **Legacy Endpoints Cleanup:** Linked `BookingSerializer` and owner-only access controls to `ListingBookingsView`.

## [0.9.0] - 2026-07-21

### Added
- **AWS Production Infrastructure Setup:** Deployed containerized production runtime stack (`Dockerfile.prod`, `entrypoint.prod.sh`, `docker-compose.prod.yml`, Nginx reverse proxy) featuring IMDSv2 dynamic public IP detection for `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.
- **Terraform Infrastructure as Code (IaC):** Added minimal Terraform module in `deploy/terraform/` for automated EC2 instance provisioning and Docker bootstrap.

### Fixed
- **Windows Process Execution Stability:** Configured `-P solo` worker execution pool patch for stable local development without process pool permissions or handle errors (`PermissionError 13` / `WinError 6`).
- **Database Engine Interoperability:** Ensured seamless operational continuity across SQLite and MySQL database backends for background task schedules.
- **Git Security Rules for IaC:** Updated `.gitignore` to explicitly ignore Terraform state files (`*.tfstate`), execution plans (`*.tfplan`), local `.terraform/` cache, and sensitive variable files (`*.tfvars`).

## [0.8.0] - 2026-07-20

### Added
- **Asynchronous Task Queue & Broker Architecture (Issue #76):** Integrated **Redis** as a Dual-Purpose Broker (`db/0`) and High-Performance Cache Storage (`db/1`), alongside **Celery** as an asynchronous task execution engine.
- **Dynamic Task Scheduling Layer (Issue #76):** Deployed `django-celery-beat` with `DatabaseScheduler`, exposing live crontab and interval task management via the Django Admin interface.
- **Background Task Implementations (Issue #76):** Built standalone Celery tasks (`apps.bookings.tasks.run_process_bookings` every 15 mins, and `apps.pricing.tasks.run_update_listing_current_price` daily at 00:05) triggering underlying Django management commands asynchronously.

### Fixed
- **Windows Process Execution Stability:** Configured `-P solo` worker execution pool patch for stable local development without process pool permissions or handle errors (`PermissionError 13` / `WinError 6`).
- **Database Engine Interoperability:** Ensured seamless operational continuity across SQLite and MySQL database backends for background task schedules.

## [0.7.0] - 2026-07-19

### Added
- Comprehensive custom data seeding system (`seed_fake_data` management command).
- Full German localization dataset (~2,600 name combinations, top 100+ cities with realistic districts, and 68 street types).
- Dynamic title builder for property listings mixing adjectives, property types, and specific features.
- Expanded review comment pools (15 positive and 15 mixed templates) for organic-looking feedback.

### Fixed
- Handled `IntegrityError` unique constraint collisions on user nicknames by automatically appending random suffixes.

## [0.6.0] - 2026-07-19

### Added
- **Cron Infrastructure Automation & Command Registrations (Issue #70):** Developed and successfully registered dedicated Django management commands (`process_bookings` and `update_listing_current_price`) to handle critical automated routines. Relocated module packages directly into application runtimes (`apps/bookings/management/commands/` and `apps/pricing/management/commands/`) to guarantee correct discovery hooks via Django's `call_command` engine.

### Fixed
- **System-Wide Timezone Drift Mitigation (Issue #70):** Resolved critical execution timeline bugs within the background scheduling layer. Replaced unstable server-wide `timezone.now()` (UTC) queries with synchronized `timezone.localtime()` calls inside the booking auto-cancellation evaluator, bringing background task iterations into perfect alignment with localized business hour constraints (`calculate_auto_cancel_deadline`).
- **Concurrent Thread-Safety & Optimization (Issue #68):** Hardened the analytics application layer by migrating `AdminDashboardStatsView` service instantiations away from persistent class attributes and directly into the request processing lifecycles, mitigating state leakage hazards under concurrent multi-worker production configurations.
- **Database Query Acceleration & Performance Caching (Issue #68):** Eliminated costly N+1 database queries inside the `AdminDashboardStatsService` gap analysis engine by applying explicit `.select_related('user')` pre-fetches. Integrated a robust performance caching strategy for heavy platform summaries to bypass real-time aggregate operations across core tracking ledgers during dashboard reloads.
- **Decoupled Test Architecture & Log Ledger Security (Issues #68, #70):** Refactored the analytical test suites to communicate strictly through public domain interfaces, retiring fragile manager monkey-patching patterns (`LogQuerySet`). Validated robust validation guards protecting the immutable historical log structure of `PriceHistory` database records against unauthorized mutations or bulk deletions.

## [0.5.0] - 2026-07-18

### Added
- **Full Application Containerization & Orchestration (Issues #44, #64):** Containerized the Django ecosystem utilizing a custom `python:3.12-slim` Dockerfile alongside an automated healthcheck-dependent `entrypoint.sh` routine executing automatic database migrations and administrative superuser bootstrapping. Deployed isolated, named Docker volumes (`db_data`) mapped to `./dump` via a clean `/docker-entrypoint-initdb.d` path, achieving instant database seeding from localized SQL dumps without exposing sensitive configuration assets to version control.
- **Interactive OpenAPI 3.0 Document Engines (Issue #60):** Integrated `drf-spectacular` schema compilation engines to dynamically expose `/api/v1/schema/`, `/api/v1/schema/swagger-ui/`, and `/api/v1/schema/redoc/`. Tailored deep schema overrides mapping specialized token delivery pathways, explicitly documenting server-side `HttpOnly` `Set-Cookie` injections, anonymous namespace bypass behaviors for registration/login controllers, and structural `X-Access-Token` response headers.
- **Production-Ready Unified Logging & Observability (Issue #62):** Integrated `sentry-sdk` tracking engines dynamically restricted to production runtime modes for automatic capturing of multi-variant database exceptions and user contexts. Layered high-volume Django logging routers operating an environment-switched console `StreamHandler` for effortless AWS CloudWatch/Docker log aggregation alongside an isolated, local-only 5MB `RotatingFileHandler` lifecycle system.

## [0.4.0] - 2026-07-17

### Added
- **Global URL Routing Blueprint (Issue #36):** Deployed root API configuration with strict `api/v1/` route isolation. Integrated `SimpleRouter` layers across all standard modules supported by controller placeholder stubs to ensure clean `manage.py check` boots.
- **Secure Authentication & Token Refresh (Issue #38):** Migrated authorization pipelines to flat `/api/v1/auth/` namespaces. Replaced insecure transport fields with server-side `HttpOnly`, `Secure` browser cookies. Implemented independent `ScopedRateThrottle` rules guarding registration spam via strict 5-requests/min IP limits.
- **Unified Analytics & Metrics Pipeline (Issues #40, #50):** Finalized profile-scoped user search history workflows and anonymous keyword metrics. Implemented a data-driven `AdminDashboardStatsView` featuring date-range gap analysis, missing-catalog counters, and a 15-minute sliding deduplication cache window.
- **3-Tier Property & Room Architecture (Issue #46):** Hardened structural boundaries across listing domains. Enforced nested coordinate checks ($[-90, 90]$ / $[-180, 180]$ ranges), model-level XOR constraints for append-only `PriceHistory` logging, and dynamic $available\_count$ mathematical annotations for multi-unit room allocations.
- **Transactional Booking & Dispute Engines (Issue #48):** Built atomic booking state-machines supporting locked price calculations and automated 15%/10% last-minute discount modifiers. Wired transactional dispute reviews alongside administrative CRUD tables for soft-deletable `CancellationReason` nodes.
- **Decoupled Review Processing (Issue #52):** Introduced isolated review controller hooks tied directly to validated text schemas. Handled strict constraints prohibiting duplicate record entry or unauthenticated rating overrides.
- **Asynchronous Notification & Signal Logging (Issue #54):** Deployed decoupled notification log factories wired directly to Django lifecycle signals, preventing thread-blocking deadlocks or circular import execution faults.
- **Media Asset Management Logic (Issue #56):** Completed the internal payload mappings, service workflows, and data queries handling secure multi-photo ingestion and metadata tracking for listing properties.

## [0.3.0] - 2026-07-13

### Added
- **Global Domain Dictionaries & Choices (Issues #19, #20):** Introduced centralized, independent choices layers for `listings`, `bookings`, `reviews`, and `notifications`. Deployed the foundational `Amenity` dictionary model with soft-delete behaviors enabled.
- **Core Property Infrastructure & Validation (Issue #21):** Implemented core `Listing` (Timestamped) and `Room` (BaseModel) schemas. Integrated localized field constraints via Django property validators (latitude/longitude ranges, capacity baselines) and multi-field cross-checks inside `Room.clean()` to reject room attachments on apartment listing types.
- **Content Assets & Price Ledger (Issue #22):** Deployed the `Photo` model utilizing explicit exclusive-OR bindings to either a Listing or a Room via model layer clean checks and database `CheckConstraint` blocks. Added the append-only `PriceHistory` ledger inheriting from `LogModel` with hooks preventing retrospective historical price mutations.
- **Transactional Booking & Dispute Layer (Issues #23, #24):** Engineered `Booking`, `Review`, and `Dispute` domain schemas. Enforced data-integrity rules directly in MySQL via database `CheckConstraint` blocks (`check_out_date > check_in_date`), multi-field capacity validation against parent listing structures, and isolated review state gates restricted exclusively to completed operations.
- **Analytical Event Logging & Deduplication (Issue #25):** Wired `SearchHistory` and `ViewHistory` pipelines using performance-indexed `LogModel` data layouts. Implemented query-string normalizers, denormalized metrics (`views_count`, `reviews_count`) on listings, and a 15-minute sliding session window for view event deduplication.

### Changed
- **Global Codebase Refactoring & Standardized App Packages (Issue #32):** Retired monolithic `models.py` architectures across all operational modules.

## [0.2.0] - 2026-07-08

### Added
- **Code Quality Pipeline (Issue #8):** Integrated strict repository linting and formatting via `black`, `isort`, and `flake8`. Introduced custom rule matrices inside root `pyproject.toml` and `.flake8` configs to enforce consistent line lengths and ignore auto-generated database migrations.
- **Base Abstract Models (Issue #9):** Established foundational architecture in `core/models.py`. Implemented `BaseModel` using UUID4 primary keys, auto-updating entity lifecycle timestamps, and a robust soft-delete mechanic controlled via an overridden `delete()` method. Developed an `ActiveManager` (default `objects` lookups) and an `all_objects` manager to fetch soft-deleted datasets. Created a `TimestampedModel` for non-deletable records, and a `LogModel` for append-only pipelines.
- **Custom User Model & System Roles (Issue #10):** Built the `apps/users` domain layer inheriting from `AbstractBaseUser` and `PermissionsMixin`, migrating from username identifiers to case-insensitive emails. Added an integer `token_version` column to handle instantaneous multi-device session revocation. Defined robust system roles (`tenant`, `landlord`, `moderator`, `admin`) under `apps/security/constants.py` supported by an automated group-provisioning database data migration.
- **EU Gender Layout Compliance:** Decoupled data layout logic by introducing `apps/users/choices.py`. Added an optional alphanumeric `gender` state field (`M` for Male, `F` for Female, `X` for Other) matching clean architecture paradigms and European identity metadata standards.
- **JWT Authorization Layer & Middleware (Issue #11):** Wired `djangorestframework-simplejwt` to split token delivery pathways safely. Client apps ingest short-lived access keys in plain JSON responses, while the refresh mechanism is securely locked inside an `HttpOnly`, `Secure`, `SameSite=Lax` browser cookie. Auth requests pass through a custom automated token rotation and validation middleware (`apps/security/middleware.py`) cross-referencing active session integrity with database `token_version` fields.

### Changed
- **Immutable Log Security Enforcement:** Hardened abstract `LogModel` behaviors by overriding the `.delete()` method to natively reject hard or soft lifecycle deletions with an explicit `ValidationError`.
- **Dual-Layer Email Identity Normalization:** Anchored comprehensive `.lower().strip()` string normalizers within both the custom `UserManager._create_user` factory and the model level `User.save()` state hook to completely block duplicate variant entries.
- **Django Admin Architecture Overhaul:** Fully rewrote user management registration and editing layouts inside `apps/users/admin.py`. Forms now explicitly inherit from native `UserCreationForm` and `UserChangeForm` classes, resolving type-safety constraints while clearing out conflicting legacy `username` properties via custom constructors.

## [0.1.0] - 2026-07-07

### Added
- **Initial Backend Foundation (Issue #1):** Configured base Django project setup, local environment variables via `django-environ`, and a secure `.env.example` template.
- **MySQL Connection:** Configured local MySQL connectivity within Django settings with fallback to SQLite3 for flexible local development.
- **Media Support Setup:** Added base media settings (`MEDIA_URL` and `MEDIA_ROOT`) to lay the groundwork for future file uploads.
- **Initial Django App Structure (Issue #3):** Created and registered core and domain-specific applications (`core`, `users`, `listings`, `content`, `bookings`, `pricing`, `reviews`, `analytics`, `notifications`) inside the newly structured layout.
- **Documentation:** Added detailed MVP technical specifications, development agreements, and a staged backend implementation roadmap to `README.md`.

### Changed
- Replaced the initial minimal repository description with a comprehensive project scope and architecture roadmap.
- Migrated primary database scope from PostgreSQL to MySQL for local containerized development and AWS RDS compatibility.
- Clarified structural boundaries between the `config` configuration package and the `core` shared infrastructure application.

## Unreleased

### Added

- Added MVP technical specification to `README.md`.
- Added staged backend implementation roadmap.
- Added changelog file for future task tracking.
- Added media/content scope for listing and room photo uploads.
- Added contributing guide with protected-branch Git workflow.
- Added initial Django app structure planning with a dedicated `content` app for media-related domain data.
