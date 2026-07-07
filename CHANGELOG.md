# Changelog

All notable changes to LodgixHub will be documented in this file.

The format follows a simple chronological structure.

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
