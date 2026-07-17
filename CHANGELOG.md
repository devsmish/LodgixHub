# Changelog

All notable changes to LodgixHub will be documented in this file.

The format follows a simple chronological structure.

## [0.4.0] - 2026-07-17

### Added
- **Global URL Routing Blueprint (Issue #26):** Deployed root API configuration with strict `api/v1/` route isolation. Integrated `SimpleRouter` layers across all standard modules supported by controller placeholder stubs to ensure clean `manage.py check` boots.
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
